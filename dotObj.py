import cv2
import numpy
import scipy.ndimage.filters
import time

class dotObj:
	def __init__(self,name,isFid,xPixel,yPixel,radiusPixel,blinkCriterion,blurSize,filterSize):
		self.name = name
		self.isFid = isFid
		self.xPixel = xPixel
		self.yPixel = yPixel
		self.radiusPixel = radiusPixel
		self.radius = radiusPixel
		self.first = True
		self.radii = []
		self.SDs = []
		self.lostCount = 0
		self.blinkCriterion = blinkCriterion
		self.blurSize = blurSize
		self.filterSize = filterSize
	def getDarkEllipse(self,img):
		#if not self.isFid:
		#	#cv2.imwrite(self.name + "_" + "%.2d" % imageNum + "_raw.png" , img)
		try:
			smoothedImg = cv2.GaussianBlur(img,(self.blurSize,self.blurSize),0)
			#if not self.isFid:
			#	#cv2.imwrite(self.name + "_" + "%.2d" % imageNum + "_smoothed.png" , img)
		except:
			print 'cv2.GaussianBlur failed'
			# cv2.imwrite('temp.png',img)
			return None
		try:
			dataMin = scipy.ndimage.filters.minimum_filter(smoothedImg, self.filterSize)
		except:
			print 'scipy.ndimage.filters.minimum_filter failed'
			# cv2.imwrite('temp.png',img)
			return None
		if dataMin!=None:
			try:
				minLocs = numpy.where(dataMin<(numpy.min(dataMin)+numpy.std(dataMin)))
			except:
				print 'numpy.where failed'
				# cv2.imwrite('temp.png',img)
				return None
			if len(minLocs[0])>=5:
				try:
					ellipse = cv2.fitEllipse(numpy.reshape(numpy.column_stack((minLocs[1],minLocs[0])),(len(minLocs[0]),1,2)))
				except:
					print 'cv2.fitEllipse failed'
					# cv2.imwrite('temp.png',img)
					return None
				return ellipse

	def cropImage(self,img,cropSize):
		xLo = self.xPixel - cropSize
		if xLo<0:
			xLo = 0
		xHi = self.xPixel + cropSize
		if xHi>img.shape[1]:
			xHi = img.shape[1]
		yLo = self.yPixel - cropSize
		if yLo<0:
			yLo = 0
		yHi = self.yPixel + cropSize
		if yHi>img.shape[0]:
			yHi = img.shape[0]
		return [img[yLo:yHi,xLo:xHi],xLo,xHi,yLo,yHi]
	def search(self,img):
		if self.lost or self.first:
			searchSize = 5
		else:
			searchSize = 3
		if self.first:
			self.first = False
		img,xLo,xHi,yLo,yHi = self.cropImage(img=img,cropSize=searchSize*self.radiusPixel)
		self.ellipse = self.getDarkEllipse(img=img,imageNum=imageNum)
		if self.ellipse!=None:
			self.ellipse = ((self.ellipse[0][0]+xLo,self.ellipse[0][1]+yLo),self.ellipse[1],self.ellipse[2])
			self.lost = False
			self.x = self.ellipse[0][0]
			self.y = self.ellipse[0][1]
			self.major = self.ellipse[1][0]
			self.minor = self.ellipse[1][1]
			self.angle = self.ellipse[2]
			self.xPixel = int(self.x)
			self.yPixel = int(self.y)
			self.radius = (self.ellipse[1][0]+self.ellipse[1][1])/4
			self.radiusPixel = int(self.radius)
		else:
			self.lost = True
	def checkSearch(self):
		self.medianRadius = numpy.median(self.radii)
		self.critRadius = 10*((numpy.median((self.radii-self.medianRadius)**2))**.5)
		#print [self.name, self.radius2,(self.radius2<(1/6)) , (self.radius2>2)]
		if len(self.radii)<30:
			self.radii.append(self.radius2)
			self.lost = False
		else:
			#fid diameter is 6mm, so range from 1mm to 12mm
			#if (self.radius2<(1/6)) or (self.radius2>2) or (self.radius2<(self.medianRadius - self.critRadius)) or (self.radius2>(self.medianRadius + self.critRadius)):
			if (self.radius2<(1/6)) or (self.radius2>2):
				self.lost = True
			else:
				self.lost = False
				self.radii.append(self.radius2)
			if len(self.radii)>=300:
				self.radii.pop()
	def makeRelativeToFid(self,fid):
		self.x2 = (self.x-fid.x)/fid.radius
		self.y2 = (self.y-fid.y)/fid.radius
		self.radius2 = self.radius/fid.radius
	def checkSD(self,img,fid):
		self.obsSD = numpy.std(self.cropImage(img=img,cropSize=5*fid.radiusPixel)[0])
		self.medianSD = numpy.median(self.SDs)
		self.critSD = self.medianSD*self.blinkCriterion
		#print [self.name,self.obsSD,self.medianSD,self.critSD,self.blinkCriterion]
		if len(self.SDs)<30:
			self.SDs.append(self.obsSD)
			self.blink = False
		else:
			if (self.obsSD<self.critSD):
				self.blink = True
			else:
				self.SDs.append(self.obsSD)
				self.blink = False
			if len(self.SDs)>=300:
				self.SDs.pop()
	def update(self,img,fid=None):
		lastPixels = [self.xPixel,self.yPixel,self.radiusPixel]
		if self.isFid:
			self.search(img=img)
		else:
			self.checkSD(img=img,fid=fid) #alters the value of self.blink, amongst other things
			if self.blink:
				self.xPixel,self.yPixel,self.radiusPixel = lastPixels
			else:
				self.search(img=img) #alters the value of self.lost, amongst other things
				if self.lost:
					self.xPixel,self.yPixel,self.radiusPixel = lastPixels
				else:
					self.makeRelativeToFid(fid=fid)
					self.checkSearch() #alters the value of self.lost, among other things
					if self.lost:
						self.xPixel,self.yPixel,self.radiusPixel = lastPixels
		if self.lost and not self.blink:
			self.lostCount += 1
		else:
			self.lostCount = 0
