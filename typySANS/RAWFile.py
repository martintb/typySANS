import struct
import numpy as np
import os

class RAWFile(object):
  def __init__(self,fileName):
    self.reset(fileName)

  def reset(self,fileName):
    self.fileName = fileName
    self.SANSData = {}
    self.fileBytes = None

  def __getitem__(self,key):
    return self.SANSData[key]

  def readFile(self,force=False):
    if force or (self.fileBytes is not None): #already read
      return

    print('--> Reading all bytes from {}'.format(os.path.basename(self.fileName)))
    with open(self.fileName,'rb') as f:
      self.fileBytes = f.read()

  def isRAW(self):
    '''
    Based on translated NCNR_SANS_Package_7.50/NCNR_User_Procedures/Reduction/SANS/NCNR_Utils.ipf
    '''
    self.readFile()

    fileSize = len(self.fileBytes)
    if len(self.fileBytes)<100:
      print('==> Not RAW! File too small to be RAW.')
      return False

    if not (fileSize == 33316): 
      print('==> Not RAW! File size incorrect ({} != 33316).'.format(fileSize))
      return False

    runType = self.readChars(start=75,num=3)
    if not (('RAW' in runType) or ('SIM' in runType)):
      print('==> Not RAW! Run type is incorrect ({} != RAW or SIM).'.format(runType))
      return False

    print('--> {} appears to be RAW!'.format(os.path.basename(self.fileName)))
    return True

  def readInts(self,start,num):
    size = 4 # unsigned ints are 4 bytes4
    return struct.unpack(num*'I',self.fileBytes[start:start+num*size])

  def readShorts(self,start,num):
    size = 2 # unsigned shorts are 2 bytes
    return struct.unpack(num*'H',self.fileBytes[start:start+num*size])

  def readChars(self,start,num):
    size = 1 #chars are 1 byte
    chars = struct.unpack(num*'c',self.fileBytes[start:start+num*size])

    # For some reason, some files have bogus characters in them so we
    # have to manually handle bad bytes.
    outStr = ''
    for c in chars:
      try:
        outStr += c.decode('UTF-8')
      except UnicodeDecodeError:
        outStr += '!'
    return outStr

  def readIEEEFloats(self,start,num):
    size = 4 # single-precision floats are 4 bytes
    return struct.unpack(num*'f',self.fileBytes[start:start+num*size])

  def readVAXFloats(self,start,num):
    size = 4 # vAXS 32 bit floats are 4 bytes
    vals = [self.VAXtoFloat(self.fileBytes[start+i*size:start+(i+1)*size]) for i in range(num)]
    return vals

  def VAXtoFloat(self,stream):
    '''
    Unfortunately this is somewhat of a black box. I was unable to locate an availble open-
    source utility to reax VAX floats from a file and even this blog post was not easy to find.
    At the very least, it is based on a usgs codebase so we could rewrite ourselves based on the 
    (likely free and open) original.

    modified from: http://yaadc.blogspot.com/2013/01/vax-ffloat-and-dfloat-to-ieee-tfloat.html
    based on: https://pubs.usgs.gov/of/2005/1424/
    '''
    SIGN_BIT = 0x80000000
    VAX_F_MANTISSA_MASK = 0x007FFFFF
    VAX_F_MANTISSA_SIZE = 23
    VAX_F_HIDDEN_BIT    = (1 << VAX_F_MANTISSA_SIZE)
    VAX_F_EXPONENT_SIZE = 8
    VAX_F_EXPONENT_BIAS = (1 << (VAX_F_EXPONENT_SIZE - 1))
    VAX_F_EXPONENT_MASK = 0x7F800000
    IEEE_S_EXPONENT_SIZE = 8
    IEEE_S_EXPONENT_BIAS = ((1 << (IEEE_S_EXPONENT_SIZE - 1)) - 1)
    IEEE_S_MANTISSA_SIZE = 23
    EXPONENT_ADJUSTMENT = (1 + VAX_F_EXPONENT_BIAS - IEEE_S_EXPONENT_BIAS)
    IN_PLACE_EXPONENT_ADJUSTMENT = (EXPONENT_ADJUSTMENT << IEEE_S_MANTISSA_SIZE)
  
    v1a, v1b = struct.unpack('HH', stream)
    v1 = v1b + 65536 * v1a
  
    e = v1 & VAX_F_EXPONENT_MASK
  
    if e == 0:
      if v1 & SIGN_BIT == SIGN_BIT:
          raise
      res = bytes('\x00' * 4,encoding='UTF-8')
    else:
      e >>= VAX_F_MANTISSA_SIZE
      e -= EXPONENT_ADJUSTMENT
  
      if e > 0:
          res = v1 - IN_PLACE_EXPONENT_ADJUSTMENT
      else:
          res = (v1 & SIGN_BIT) | ((VAX_F_HIDDEN_BIT | (v1 & VAX_F_MANTISSA_MASK)) >> (1 - e))
  
      #TBM: original method threw error because res was 8 bytes long
      # res = struct.pack('L', res)
      res = struct.pack('L', res)[:4]
    return struct.unpack('f', res)[0]

  def printHeader(self):
    print('--> Displaying all header data...')
    keys = sorted(self.SANSData.keys())
    for k in keys:
      if k != 'rawCounts':
        print('{:20s}:'.format(k),self.SANSData[k])

  def readHeader(self):
    '''
    Based on translated NCNR_SANS_Package_7.50/NCNR_User_Procedures/Reduction/SANS/NCNR_DataReadWrite.ipf
    '''
    print('--> Processing bytes from header...')
    SANSData = self.SANSData

    SANSData['fileName']    = self.readChars(start=2,num=21)
    SANSData['runTimeDate'] = self.readChars(start=55,num=20)
    SANSData['runType']     = self.readChars(start=75,num=3)
    SANSData['runDefDir']   = self.readChars(start=78,num=11)
    SANSData['runMode']     = self.readChars(start=89,num=1)
    SANSData['runReserve']  = self.readChars(start=90,num=8)
    SANSData['sampleLabel'] = self.readChars(start=98,num=60)

    a,b,c,d = self.readInts(start=23,num=4)
    SANSData['npre']      = a
    SANSData['countTime'] = b
    SANSData['runTime']   = c
    SANSData['numRuns']   = d
    
    a,b,c = self.readInts(start=174,num=3)
    SANSData['sampleTable']  = a
    SANSData['sampleHolder'] = b
    SANSData['sampleBlank']  = c
    
    a,b = self.readInts(start=194,num=2)
    SANSData['sampleTctrlr'] = a
    SANSData['sampleMagnet'] = b
    
    SANSData['sampleTUnits'] = self.readChars(start=202,num=6)
    SANSData['sampleFUnits'] = self.readChars(start=208,num=6)
    SANSData['detectorType'] = self.readChars(start=214,num=6)
    
    a,b = self.readInts(start=244,num=2)
    SANSData['detectorNum']    = a
    SANSData['detectorSpacer'] = b
    
    a,b = self.readInts(start=308,num=2)
    SANSData['tsliceMultFact'] = a
    SANSData['tsliceLTSlice']  = b
    
    a,b = self.readInts(start=332,num=2)
    SANSData['tempExtra']  = a
    SANSData['tempErrInt'] = b
    
    a,b,c = self.readInts(start=376,num=3)
    SANSData['paramsBlank1'] = a
    SANSData['paramsBlank2'] = b
    SANSData['paramsBlank3'] = c
    
    SANSData['paramsReserve']  = self.readChars(start=404,num=42)
    SANSData['voltageSpacer'], = self.readInts(start=458,num=1)
    
    a,b,c,d = self.readInts(start=478,num=4)
    SANSData['analysisRows1'] = a
    SANSData['analysisRows2'] = b
    SANSData['analysisCols1'] = c
    SANSData['analysisCols2'] = d
    
    SANSData['tsliceSlicing'],        = self.readInts(start=304,num=1)
    SANSData['tempPrintTemp'],        = self.readInts(start=316,num=1)
    SANSData['magnetPrintMag'],       = self.readInts(start=340,num=1)
    SANSData['magnetSensor'],         = self.readInts(start=344,num=1)
    SANSData['voltagePrintTemp'],     = self.readInts(start=446,num=1)
    SANSData['polarizationPrintPol'], = self.readInts(start=462,num=1)
    SANSData['polarizationFlipper'],  = self.readInts(start=466,num=1)
    
    a,b,c,d= self.readVAXFloats(start=39,num=4)
    SANSData['runMonitorCount']  = a
    SANSData['runSaveMonitor']   = b
    SANSData['runDetectorCount']  = c
    SANSData['runAttenuatorNum']  = d
    
    a,b,c,d= self.readVAXFloats(start=158,num=4)
    SANSData['sampleTransmission']  = a
    SANSData['sampleThickness']     = b
    SANSData['samplePosition']      = c
    SANSData['sampleRotationAng']        = d
    
    a,b = self.readVAXFloats(start=186,num=2)
    SANSData['sampleTemp']   = a
    SANSData['sampleField']  = b
    
    a,b,c,d,e,f = self.readVAXFloats(start=220,num=6)
    SANSData['calX1']   = a
    SANSData['calX2']   = b
    SANSData['calX3']   = c
    SANSData['calY1']   = d
    SANSData['calY2']   = e
    SANSData['calY3']   = f
    
    vals = self.readVAXFloats(start=252,num=13)
    SANSData['detectorBeamX']          = vals[0]
    SANSData['detectorBeamY']          = vals[1]
    SANSData['detectorDistance']       = vals[2]
    SANSData['detectorOffset']         = vals[3]
    SANSData['detectorSize']           = vals[4]
    SANSData['detectorBeamStop']       = vals[5]
    SANSData['detectorBlank']          = vals[6]
    SANSData['resolutionAP1']     = vals[7]
    SANSData['resolutionAP2']     = vals[8]
    SANSData['resolutionAP1DIS']  = vals[9]
    SANSData['resolutionLambda']  = vals[10]
    SANSData['resolutionDLambda'] = vals[11]
    SANSData['resolutionNLenses'] = vals[12]
    
    a,b,c = self.readVAXFloats(start=320,num=3)
    SANSData['tempHold']      = a
    SANSData['tempErrFloat']  = b
    SANSData['tempBlank']     = c
    
    vals = self.readVAXFloats(start=348,num=7)
    SANSData['magnetCurrent']      = vals[0]
    SANSData['magnetConv']         = vals[1]
    SANSData['magnetFieldLast']    = vals[2]
    SANSData['magnetBlank']        = vals[3]
    SANSData['magnetSpacer']       = vals[4]
    SANSData['beamStopX']          = vals[5]
    SANSData['beamStopY']          = vals[6]
    
    vals = self.readVAXFloats(start=388,num=4)
    SANSData['paramsTrnsCount']     = vals[0]
    SANSData['paramsExtra1']        = vals[1]
    SANSData['paramsExtra2']        = vals[2]
    SANSData['paramsExtra3']        = vals[3]
    
    a,b = self.readVAXFloats(start=450,num=2)
    SANSData['voltageVolts']     = vals[0]
    SANSData['voltageBlank']     = vals[1]
    
    a,b = self.readVAXFloats(start=470,num=2)
    SANSData['polarizationHoriz']    = vals[0]
    SANSData['polarizationVert']     = vals[1]

    print('--> Done processing header!')

  def readDetector(self):
    # So the num value here is kind of magic...  We know it starts on byte 514, but during
    # the decompression step, there's all kinds of weirdness where every 1023 integer is 
    # skipped. So basically, even though we only have 128*128=16384 pixels on the detector,
    # we need to read many more integers from this section of the file. Even more unfortunate
    # is that Igor magically determines how many integers read at this point. I believe the 
    # resulting code below reads the rest of the file, but I'm not entirely sure. It works....
    print('--> Reading detector counts...')
    num = len(self.fileBytes[514:])//2
    rawDet = self.readShorts(start=514,num=num)
    rawDet = np.array(self.SkipAndDecompress(rawDet)).reshape((128,128))
    self.SANSData['rawCounts']     = rawDet
    print('--> Done reading detector counts!')
  
  def SkipAndDecompress(self,arr_in):
    '''
    Directly translated from NCNR_SANS_Package_7.50/NCNR_User_Procedures/Reduction/SANS/NCNR_DataReadWrite.ipf
    '''
    arr_out = []
    ii = 0
    skip = 0
    while ii<16384:
      if (((ii+skip)%1022)==0):
        skip+=1
      arr_out.append(self.Decompress(arr_in[ii+skip]))
      ii+=1
    return arr_out
  
  def Decompress(self,val):
    '''
    Directly translated from NCNR_SANS_Package_7.50/NCNR_User_Procedures/Reduction/SANS/NCNR_DataReadWrite.ipf
    '''
    ib = 10
    nd = 4
    ipw = ib**(nd)
    i4 = val
    if (i4<-ipw):
      npw = -i4/ipw
      i4 = ((-i4)%ipw)*(ib**(npw))
    return i4
