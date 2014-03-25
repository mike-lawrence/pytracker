#pytracker

A python package for interacting with a webcam for gaze tracking &amp; pupillometry. Currently only has accounting for head movements in x,y,z planes only; translations in pitch, roll and yaw are on the to-do list.


##Software dependencies

 - numpy (http://numpy.org)
 - scipy (http://scipy.org)
 - OpenCV (http://opencv.org)
 - billiard (https://github.com/celery/billiard)


##Hardware dependencies

Eye tracking is more reliable if using an infrared sensitive camera and a source of infrared illumination. This is because most users' skin and iris color will be a light grey under these conditions, making detection of a dark pupil easier. Consumer webcams can easily be modified (how-to video coming soon) to see in the infrared by removing the infrared block-filter included by the manufacturer and adding an infrared pass-fileter (this one is <$10: http://goo.gl/eCK7yv ). An infrared light source can be obtained cheaply from many places, including a Nintendo Wii "sensor" bar (which is really just an infrared light source). The wireless Wii sensor bars can be moded (how-to video coming soon) to be USB powered if you don't want to keep wasting batteries. 

Finally, the code expects that the user has a black dot on their head, placed between the eyes and just above the brow. This dot serves as a reference point for the head's location so that eye movements can be dissociated from head movements. The tracker additionally expects that the dot's size is a standard hole-punch size. A good way to create such dots is to use a laser printer (these use infrared opaque inks) to print a page of solid black onto a sheet of adhesive label paper, then use a hole punch to punch out the dots as needed.


##Example usage

```python
if __name__ == '__main__':
	import pytracker
	import time
	camIndex = 1
	camRes = [1920,1080]
	previewDownsize = 2
	timestampMethod = 0
	tracker = pytracker.trackerClass(camIndex=camIndex,camRes=camRes,previewDownsize=previewDownsize,timestampMethod=timestampMethod)
	tracker.start()
	while True:
		time.sleep(1)
		if not tracker.qFrom.empty():
			message = tracker.qFrom.get()
			if message=='done':
				break
```
Press '0' to begin tracking once the video preview window appears.
