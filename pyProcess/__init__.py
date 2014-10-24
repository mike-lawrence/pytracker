import billiard
billiard.forking_enable(0)

########
# Define a class that spawns a new process
########
class processClass:
	def __init__(self,fileToRun):
		self.fileToRun = fileToRun
		self.initVars = {}
		self.qTo = billiard.Queue()
		self.qFrom = billiard.Queue()
		self.started = False
	def f(self,fileToRun,qTo,qFrom,**initVars):
		l = locals()
		for n, v in initVars.items():
			l[n] = v
		execfile(fileToRun)
	def start(self):
		if self.started:
			print 'Oops! Already started this process.'
		else:
			self.process = billiard.Process( target=self.f , args=(self.fileToRun,self.qTo,self.qFrom,),kwargs=self.initVars )
			self.process.start()
			self.started = True
	def isAlive(self):
		return self.process.is_alive()
	def stop(self,killAfter=None):
		if not self.started:
			print 'Oops! Not started yet!'
		else:
			self.qTo.put('quit')
			self.process.join(timeout=killAfter)
			if self.process.is_alive():
				self.process.terminate()
		return None

