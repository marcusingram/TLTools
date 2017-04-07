import datetime
import numpy as np
from ctypes import windll, c_char_p, c_ushort, c_int, byref, c_ulonglong, c_double


class FMC:
    def __init__(self, Fs, Ts):
        self.Fs = Fs
        self.time_start = Ts
        self.FMC = []
        self.Unpacked = False

    def uploadStream(self, I16):
        self.Stream = I16
        self.timestamp = datetime.datetime.utcnow()
        self.Unpacked = False

    def uploadLUT(self, LUT, Step, Samples):
        self.LookupTable = LUT
        self.SampleStep = Step
        self.n_samples = Samples

    def getAScan(self, tx, rx):
        start_sample = self.LookupTable[tx, rx]
        skip = self.SampleStep
        end_sample = start_sample + skip*self.n_samples
        return self.Stream[start_sample:end_sample:skip]

    def unpack(self):
        ntx = self.LookupTable.shape[0]
        nrx = self.LookupTable.shape[1]
        unpacked = np.zeros((ntx * nrx, self.n_samples)).astype(np.int16)
        for tx in range(ntx):
            for rx in range(nrx):
                idx = tx*ntx+rx
                unpacked[idx, :] = self.getAScan(tx, rx)
        self.FMC = unpacked
        self.Unpacked = True

class DSL:
    def __init__(self, **kwargs):
        self.DSL = windll.LoadLibrary(
            #'C:/Program Files (x86)/National Instruments/LabVIEW 2013/user.lib/DSLFITacquire/DSLFITacquire.dll')
            'C:/Program Files/National Instruments/LabVIEW 2015/user.lib/DSLFITstreamFRD/DSLFITstreamFRD.dll')
        # Start the DSL software
        #VIname = encodeString('DSLFITacquire.vi')
        VIname = encodeString('DSLFITstreamFRD.vi')
        CallerID = encodeString('cueART')
        SysConfigFile = encodeString(
            'C:/Users/Public/Documents/FIToolbox/Configs/System/FITsystem.cfg')
        if 'ConfigFile' in kwargs:
            ConfigFile = encodeString(kwargs['ConfigFile'])
        else:
            ConfigFile = encodeString(
                'C:/Users/Public/Documents/FIToolbox/Configs/Setups/Default.cfg')
        self.DSL.LaunchDSLFITscan(VIname, CallerID, SysConfigFile, ConfigFile)

        # Define some default terms
        self.timeout = c_int(10000)
        self.ParamsDefined = 0
        self.LUT_initialised = 0
        self.n_tx = 0
        self.n_rx = 0
        self.n_samples = 0
        self.U64_samples = 0
        self.time_start = 0
        self.Fs = 0
        self.FMC_LUT = 0
        self.SampleStep = 0

    def getDataParams(self):
        num_frames = c_int(0)
        num_tx = c_int(0)
        num_rx = c_int(0)
        num_samples = c_int(0)
        self.DSL.GetU64dataParas(self.timeout, byref(num_frames), byref(num_tx), byref(num_rx), byref(num_samples))
        self.n_tx = num_tx.value
        self.n_rx = num_rx.value
        self.n_samples = num_samples.value
        self.n_frames = num_frames.value
        self.U64_samples = int((self.n_tx * self.n_rx * self.n_samples) / 4) # 4 I16s packed into a single U64
        Ts_select = c_int(1)
        Fs_select = c_int(2)
        output = c_double(0)
        self.DSL.SetGetParaDouble(c_int(0), self.timeout, byref(Ts_select), byref(output), c_int(1))
        self.time_start = output.value * 1e-6
        self.DSL.SetGetParaDouble(c_int(0), self.timeout, byref(Fs_select), byref(output), c_int(1))
        self.Fs = output.value
        self.ParamsDefined = 1

    def buildLookupTable(self):
        if self.ParamsDefined == 0:
            self.getDataParams()
        self.FMC_LUT = np.zeros((self.n_tx, self.n_rx)).astype(np.int32)
        U64_idx = c_int(0)
        U64_stp = c_int(0)

        Frame_ID = c_int(self.n_frames-1)
        Sample_ID = c_int(0)

        for tx in range(self.n_tx):
            for rx in range(self.n_rx):
                self.DSL.GetU64streamIndexAndStep(Frame_ID, c_int(tx), c_int(rx), Sample_ID, self.timeout, byref(U64_idx), byref(U64_stp))
                self.FMC_LUT[tx, rx] = U64_idx.value

        self.SampleStep = U64_stp.value
        self.LUT_initialised = 1

    def getU64Stream(self):
        if not self.ParamsDefined:
            self.getDataParams()
        if not self.LUT_initialised:
            self.buildLookupTable()

        Frame_ID = c_int(0)
        StartIdx = c_int(0)
        SegmentSize = c_int(self.U64_samples)
        byref(c_int(self.n_tx))
        byref(c_int(self.n_rx))
        byref(c_int(self.n_samples))
        U64Stream = (c_ulonglong * self.U64_samples)()
        self.DSL.GetU64dataStreamSegment(Frame_ID, self.timeout, StartIdx, SegmentSize, U64Stream, byref(c_int(self.n_tx)), byref(c_int(self.n_rx)), byref(c_int(self.n_samples)))
        I16Stream = np.ctypeslib.as_array(U64Stream).view(np.int16)
        newFMC = FMC(self.Fs, self.time_start)
        newFMC.uploadStream(I16Stream)
        newFMC.uploadLUT(self.FMC_LUT, self.SampleStep, self.n_samples)
        return newFMC

    def saveFMCtoPNG(self, path):
        ResponseMessage = encodeString('Reponse Message')
        SaveFRD = c_ushort(4)
        ResponseMessageLength = c_int(256)
        output = self.DSL.LoadSaveFile(SaveFRD, encodeString(path), self.timeout, ResponseMessage, ResponseMessageLength, ResponseMessage,
                                       ResponseMessageLength)
        return output

    def acquireMultiple(self, count):
        FMCs = []
        for _ in range(count):
            FMCs.append(self.getU64Stream())
        return FMCs

def encodeString(string):
    return c_char_p(string.encode('utf-8'))