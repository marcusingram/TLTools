import datetime
import numpy as np
from ctypes import windll, c_char_p, c_ushort, c_int, byref, c_ulonglong, c_double
import time
from PIL import Image

class FMC:
    def __init__(self, Fs, Ts):
        self.Fs = Fs
        self.time_start = Ts
        self.Unpacked = False
        self.timestamp = datetime.datetime.utcnow()

        self.FMC = []
        self.Stream = []
        self.LookupTable = []
        self.SampleStep = -1
        self.n_samples = -1

    def upload_stream(self, I16, LUT, Step, Samples):
        """ Upload the U64 stream (cast to I16s) and everything needed to unpack it """
        self.Stream = I16
        self.LookupTable = LUT
        self.SampleStep = Step
        self.n_samples = Samples
        self.Unpacked = False
		
	def save_to_PNG(self,path):
		Image.fromarray(self.get_FMC()).save(path, "PNG", compress_level=0,bits=16)

    def _get_AScan(self, tx, rx):
        start_sample = self.LookupTable[tx, rx]
        skip = self.SampleStep
        end_sample = start_sample + skip*self.n_samples
        return self.Stream[start_sample:end_sample:skip]

    def _unpack(self):
        ntx = self.LookupTable.shape[0]
        nrx = self.LookupTable.shape[1]
        unpacked = np.zeros((ntx * nrx, self.n_samples)).astype(np.int16)
        for tx in range(ntx):
            for rx in range(nrx):
                idx = tx*ntx+rx
                unpacked[idx, :] = self._get_AScan(tx, rx)
        self.FMC = unpacked
        self.Unpacked = True

    def get_FMC(self):
        if self.Unpacked:
            return self.FMC
        else:
            self._unpack()
            return self.FMC


class DSL:
    def __init__(self, **kwargs):
        self.DSL = windll.LoadLibrary(
            'C:/Program Files/National Instruments/LabVIEW 2015/user.lib/DSLFITstreamFRD/DSLFITstreamFRD.dll')
        VI_name = DSL._encodeString('DSLFITstreamFRD.vi')
        Caller_ID = self._encodeString('cueART')
        Sys_Config_File = self._encodeString(
            'C:/Users/Public/Documents/FIToolbox/Configs/System/FITsystem.cfg')
        if 'ConfigFile' in kwargs:
            Config_File = self._encodeString(kwargs['ConfigFile'])
        else:
            Config_File = self._encodeString(
                'C:/Users/Public/Documents/FIToolbox/Configs/Setups/Default.cfg')
        self.DSL.LaunchDSLFITscan(VI_name, Caller_ID, Sys_Config_File, Config_File)

        # Define some default terms
        self.timeout = c_int(10000)
        self.params = dict(n_tx=0,n_rx=0,n_samples=0,n_frames=0)
        self.U64_samples = 0
        self.time_start = 0
        self.Fs = 0
        self.FMC_LUT = 0
        self.SampleStep = 0

    def _check_data_params(self):
        num_frames = c_int(0)
        num_tx = c_int(0)
        num_rx = c_int(0)
        num_samples = c_int(0)
        self.DSL.GetU64dataParas(self.timeout, byref(num_frames), byref(num_tx), byref(num_rx), byref(num_samples))
        new_params = {'n_tx': num_tx.value, 'n_rx': num_rx.value, 'n_samples': num_samples.value,
                      'n_frames': num_frames.value}
        if new_params==self.params:
            return
        self.params = new_params
        self.U64_samples = int(self.params['n_tx'] * self.params['n_rx'] * self.params['n_samples'] / 4)
        Ts_select = c_int(1)
        Fs_select = c_int(2)
        output = c_double(0)
        self.DSL.SetGetParaDouble(c_int(0), self.timeout, byref(Ts_select), byref(output), c_int(1))
        self.time_start = output.value * 1e-6
        self.DSL.SetGetParaDouble(c_int(0), self.timeout, byref(Fs_select), byref(output), c_int(1))
        self.Fs = output.value
        self._build_lookup_table()

    def _build_lookup_table(self):
        self.FMC_LUT = np.zeros((self.params['n_tx'], self.params['n_rx'])).astype(np.int32)
        U64_idx = c_int(0)
        U64_stp = c_int(0)
        Frame_ID = c_int(self.params['n_frames']-1)
        Sample_ID = c_int(0)
        Times = []
        start = time.time()
        av_count = 10
        for tx in range(self.params['n_tx']):
            for rx in range(self.params['n_rx']):
                if len(Times) < av_count:
                    end = time.time()
                    Times.append(end-start)
                    start = end
                elif len(Times) == av_count:
                    mean_time = np.mean(Times[1:])
                    remaining = (self.params['n_tx'] * self.params['n_rx'] - av_count)*mean_time
                    print('Recomputing lookup-table. Approximately {} seconds remaining'.format(np.round(remaining)))
                    Times.append(-1)
                self.DSL.GetU64streamIndexAndStep(Frame_ID, c_int(tx), c_int(rx), Sample_ID, self.timeout,
                                                  byref(U64_idx), byref(U64_stp))
                self.FMC_LUT[tx, rx] = U64_idx.value
        self.SampleStep = U64_stp.value

    def _get_u64_stream(self):
        """
        This method is private as users should not be able to access it without first running check_data_params first.
        All functions that call this method should check the parameters and lookup table before running this function.
        """
        Frame_ID = c_int(0)
        StartIdx = c_int(0)
        SegmentSize = c_int(self.U64_samples)
        byref(c_int(self.params['n_tx']))
        byref(c_int(self.params['n_rx']))
        byref(c_int(self.params['n_samples']))
        U64Stream = (c_ulonglong * self.U64_samples)()
        self.DSL.GetU64dataStreamSegment(Frame_ID, self.timeout, StartIdx, SegmentSize, U64Stream,
                                         byref(c_int(self.params['n_tx'])), byref(c_int(self.params['n_rx'])),
                                         byref(c_int(self.params['n_samples'])))
        I16Stream = np.ctypeslib.as_array(U64Stream).view(np.int16)
        newFMC = FMC(self.Fs, self.time_start)
        newFMC.upload_stream(I16Stream,self.FMC_LUT, self.SampleStep, self.params['n_samples'])
        return newFMC

    def save_FMC_to_PNG(self, path):
        Response_Message = self._encodeString('Reponse Message')
        SaveFRD = c_ushort(4)
        ResponseMessageLength = c_int(256)
        output = self.DSL.LoadSaveFile(SaveFRD, self._encodeString(path), self.timeout, Response_Message,
                                       ResponseMessageLength, Response_Message,ResponseMessageLength)
        return output

    def acquire_multiple_FMCs(self, count):
        self._check_data_params()
        FMCs = []
        start = time.time()
        for _ in range(count):
            FMCs.append(self._get_u64_stream())
        print('Recorded {} FMC datasets in {} seconds'.format(count,np.round(time.time()-start)))
        return FMCs

    def acquire_single_FMC(self):
        self._check_data_params()
        return self._get_u64_stream()

    @staticmethod
    def _encodeString(string):
        return c_char_p(string.encode('utf-8'))