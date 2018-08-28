import struct
import numpy as np
import os
import datetime

from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()

from sqlalchemy import Column, Integer, String, Float, PickleType, DateTime
from sqlalchemy.exc import IntegrityError

class sqlRAWFile(Base):
  __tablename__ = 'NCNRData'
  filePath       = Column(String(),primary_key=True)
  fileName       = Column(String(21))
  fileExt        = Column(String(16))
  instrumentCode = Column(String(3))
  runTimeDate    = Column(DateTime)
  runType        = Column(String(3))
  runDefDir      = Column(String(11))
  runMode        = Column(String(1)) 
  runReserve     = Column(String(8))
  sampleLabel    = Column(String(60))

  npre      = Column(Integer)
  countTime = Column(Integer)
  runTime   = Column(Integer)
  numRuns   = Column(Integer)
  
  sampleTable   = Column(Integer)
  sampleHolder  = Column(Integer)
  sampleBlank   = Column(Integer)
  
  sampleTctrlr  = Column(Integer)
  sampleMagnet  = Column(Integer)
  
  sampleTUnits  = Column(String(6))
  sampleFUnits  = Column(String(6))
  detectorType  = Column(String(6))
  
  detectorNum    = Column(Integer)
  detectorSpacer = Column(Integer)
  
  tsliceMultFact = Column(Integer)
  tsliceLTSlice  = Column(Integer)
  
  tempExtra    = Column(Integer)
  tempErrInt   = Column(Integer)
  
  paramsBlank1 = Column(Integer)
  paramsBlank2 = Column(Integer)
  paramsBlank3 = Column(Integer)
  
  paramsReserve = Column(String(42))
  voltageSpacer = Column(Integer)
  
  analysisRows1 = Column(Integer)
  analysisRows2 = Column(Integer)
  analysisCols1 = Column(Integer)
  analysisCols2 = Column(Integer)
  
  tsliceSlicing         = Column(Integer)
  tempPrintTemp         = Column(Integer)
  magnetPrintMag        = Column(Integer)
  magnetSensor          = Column(Integer)
  voltagePrintTemp      = Column(Integer)
  polarizationPrintPol  = Column(Integer)
  polarizationFlipper   = Column(Integer)
  
  runMonitorCount  = Column(Float)
  runSaveMonitor   = Column(Float)
  runDetectorCount = Column(Float)
  runAttenutorNum  = Column(Float)
  
  sampleTransmission = Column(Float) 
  sampleThickness    = Column(Float)
  samplePosition     = Column(Float)
  sampleRotationAng       = Column(Float)
  
  sampleTemp    = Column(Float)
  sampleField   = Column(Float)
  
  calX1 = Column(Float)
  calX2 = Column(Float)
  calX3 = Column(Float)
  calY1 = Column(Float) 
  calY2 = Column(Float) 
  calY3 = Column(Float)
  
  detectorBeamX          = Column(Float)
  detectorBeamY          = Column(Float)
  detectorDistance       = Column(Float)
  detectorOffset         = Column(Float)
  detectorSize           = Column(Float)
  detectorBeamStop       = Column(Float)
  detectorBlank          = Column(Float)
  resolutionAP1          = Column(Float)
  resolutionAP2          = Column(Float)
  resolutionAP1DIS       = Column(Float)
  resolutionLambda       = Column(Float)
  resolutionDLambda      = Column(Float)
  resolutionNLenses      = Column(Float)
  
  tempHold        = Column(Float)
  tempErrFloat    = Column(Float)
  tempBlank       = Column(Float)
  
  magnetCurrent   = Column(Float)
  magnetConv      = Column(Float)
  magnetFieldLast = Column(Float)
  magnetBlank     = Column(Float)
  magnetSpacer    = Column(Float)
  beamStopX       = Column(Float)
  beamStopY       = Column(Float)
  
  paramsTrnsCount = Column(Float)
  paramsExtra1    = Column(Float)
  paramsExtra2    = Column(Float)
  paramsExtra3    = Column(Float)
  
  voltageVolts  = Column(Float) 
  voltageBlank  = Column(Float)
  
  polarizationHoriz = Column(Float) 
  polarizationVert  = Column(Float)

  rawCounts = Column(PickleType)

  @staticmethod
  def create_metadata(engine):
    Base.metadata.create_all(engine)
    
  @staticmethod
  def chunkedCommit(session,queue):
    print('>>> Adding {} files to session...'.format(len(queue)))
    for rFile in queue:
      session.add(rFile)
  
    try:
      session.commit()
    except IntegrityError:
      print('++> Error trying to do chunked commit! Rolling back...')
      session.rollback()
      return False
    else:
      print('--> Added files to database!')
  
    for rFile in queue:
      session.expunge(rFile)
    return True
  
  @staticmethod
  def individualCommits(session,queue):
    for rFile in queue:
      print('>>> Adding {} to session...'.format(rFile))
      session.add(rFile)
  
      try:
        session.commit()
      except IntegrityError:
        print('++> Error trying to do single commit! Rolling back...')
        session.rollback()
      else:
        print('--> Added file to database!')
        session.expunge(rFile)
  
  def __init__(self,filePath):
    self.reset(filePath)
  
  def __repr__(self):
    return "<sqlRAWFile(fileName=%s)>" % (self.fileName)
  
  def CheckAndReadAll(self):
    if not self.isRAW():
      return False
    self.readHeader()
    self.readDetector()
    return True
  
  def printHeader(self):
    print('--> Displaying all header data...')
    keys = sorted(self.__dict__.keys())
    for k in keys:
      if k != 'rawCounts':
        print('{:20s}:'.format(k),self.__dict__[k])
  
  def reset(self,filePath):
    self.filePath = filePath
    self.fileBytes = None
  
  def readFile(self,force=False):
    if (not force) and (self.fileBytes is not None): #already read
      return True
  
    print('--> Reading all bytes from {}'.format(os.path.basename(self.filePath)))
    try:
      with open(self.filePath,'rb') as f:
        self.fileBytes = f.read()
    except FileNotFoundError:
      print('++> Cannot open file! Check file existence and name mangling (terminal whitespace). Skipping....')
      return False
    else:
      return True
  
  def isRAW(self):
    '''
    Based on translated NCNR_SANS_Package_7.50/NCNR_User_Procedures/Reduction/SANS/NCNR_Utils.ipf
    '''
    success = self.readFile()
    if not success:
      return False
  
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
  
    print('--> {} appears to be RAW!'.format(os.path.basename(self.filePath)))
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
  
  def readHeader(self):
    '''
    Based on translated NCNR_SANS_Package_7.50/NCNR_User_Procedures/Reduction/SANS/NCNR_DataReadWrite.ipf
    '''
    print('--> Processing bytes from header...')
    self.fileName    = self.readChars(start=2,num=21)
    _,ext = os.path.splitext(self.fileName)
    self.fileExt = ext
    self.instrumentCode = ext[1:4]
    try:
      self.runTimeDate = datetime.datetime.strptime(self.readChars(start=55,num=20),r'%d-%b-%Y %H:%M:%S')
    except ValueError:
      self.runTimeDate = datetime.datetime.strptime('01-JAN-1900 01:00:00',r'%d-%b-%Y %H:%M:%S')
    self.runType     = self.readChars(start=75,num=3)
    self.runDefDir   = self.readChars(start=78,num=11)
    self.runMode     = self.readChars(start=89,num=1)
    self.runReserve  = self.readChars(start=90,num=8)
    self.sampleLabel = self.readChars(start=98,num=60)
  
    a,b,c,d = self.readInts(start=23,num=4)
    self.npre      = a
    self.countTime = b
    self.runTime   = c
    self.numRuns   = d
    
    a,b,c = self.readInts(start=174,num=3)
    self.sampleTable  = a
    self.sampleHolder = b
    self.sampleBlank  = c
    
    a,b = self.readInts(start=194,num=2)
    self.sampleTctrlr = a
    self.sampleMagnet = b
    
    self.sampleTUnits = self.readChars(start=202,num=6)
    self.sampleFUnits = self.readChars(start=208,num=6)
    self.detectorType = self.readChars(start=214,num=6)
    
    a,b = self.readInts(start=244,num=2)
    self.detectorNum    = a
    self.detectorSpacer = b
    
    a,b = self.readInts(start=308,num=2)
    self.tsliceMultFact = a
    self.tsliceLTSlice  = b
    
    a,b = self.readInts(start=332,num=2)
    self.tempExtra  = a
    self.tempErrInt = b
    
    a,b,c = self.readInts(start=376,num=3)
    self.paramsBlank1 = a
    self.paramsBlank2 = b
    self.paramsBlank3 = c
    
    self.paramsReserve  = self.readChars(start=404,num=42)
    self.voltageSpacer, = self.readInts(start=458,num=1)
    
    a,b,c,d = self.readInts(start=478,num=4)
    self.analysisRows1 = a
    self.analysisRows2 = b
    self.analysisCols1 = c
    self.analysisCols2 = d
    
    self.tsliceSlicing,        = self.readInts(start=304,num=1)
    self.tempPrintTemp,        = self.readInts(start=316,num=1)
    self.magnetPrintMag,       = self.readInts(start=340,num=1)
    self.magnetSensor,         = self.readInts(start=344,num=1)
    self.voltagePrintTemp,     = self.readInts(start=446,num=1)
    self.polarizationPrintPol, = self.readInts(start=462,num=1)
    self.polarizationFlipper,  = self.readInts(start=466,num=1)
    
    a,b,c,d= self.readVAXFloats(start=39,num=4)
    self.runMonitorCount  = a
    self.runSaveMonitor   = b
    self.runDetectorCount = c
    self.runAttenutorNum  = d
    
    a,b,c,d= self.readVAXFloats(start=158,num=4)
    self.sampleTransmission  = a
    self.sampleThickness     = b
    self.samplePosition      = c
    self.sampleRotationAng   = d
    
    a,b = self.readVAXFloats(start=186,num=2)
    self.sampleTemp   = a
    self.sampleField  = b
    
    a,b,c,d,e,f = self.readVAXFloats(start=220,num=6)
    self.calX1   = a
    self.calX2   = b
    self.calX3   = c
    self.calY1   = d
    self.calY2   = e
    self.calY3   = f
    
    vals = self.readVAXFloats(start=252,num=13)
    self.detectorBeamX          = vals[0]
    self.detectorBeamY          = vals[1]
    self.detectorDistance       = vals[2]
    self.detectorOffset         = vals[3]
    self.detectorSize           = vals[4]
    self.detectorBeamStop       = vals[5]
    self.detectorBlank          = vals[6]
    self.resolutionAP1     = vals[7]
    self.resolutionAP2     = vals[8]
    self.resolutionAP1DIS  = vals[9]
    self.resolutionLambda  = vals[10]
    self.resolutionDLambda = vals[11]
    self.resolutionNLenses = vals[12]
    
    a,b,c = self.readVAXFloats(start=320,num=3)
    self.tempHold      = a
    self.tempErrFloat  = b
    self.tempBlank     = c
    
    vals = self.readVAXFloats(start=348,num=7)
    self.magnetCurrent      = vals[0]
    self.magnetConv         = vals[1]
    self.magnetFieldLast    = vals[2]
    self.magnetBlank        = vals[3]
    self.magnetSpacer       = vals[4]
    self.beamStopX          = vals[5]
    self.beamStopY          = vals[6]
    
    vals = self.readVAXFloats(start=388,num=4)
    self.paramsTrnsCount     = vals[0]
    self.paramsExtra1        = vals[1]
    self.paramsExtra2        = vals[2]
    self.paramsExtra3        = vals[3]
    
    a,b = self.readVAXFloats(start=450,num=2)
    self.voltageVolts     = vals[0]
    self.voltageBlank     = vals[1]
    
    a,b = self.readVAXFloats(start=470,num=2)
    self.polarizationHoriz    = vals[0]
    self.polarizationVert     = vals[1]
  
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
    self.rawCounts = rawDet
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

def chunkedCommit(session,queue):
  print('>>> Adding {} files to session...'.format(len(queue)))
  for rFile in queue:
    session.add(rFile)

  try:
    session.commit()
  except IntegrityError:
    print('++> Error trying to do chunked commit! Rolling back...')
    session.rollback()
    return False
  else:
    print('--> Added files to database!')

  for rFile in queue:
    session.expunge(rFile)
  return True

def individualCommits(session,queue):
  for rFile in queue:
    print('>>> Adding {} to session...'.format(rFile))
    session.add(rFile)

    try:
      session.commit()
    except IntegrityError:
      print('++> Error trying to do single commit! Rolling back...')
      session.rollback()
    else:
      print('--> Added file to database!')
      session.expunge(rFile)
