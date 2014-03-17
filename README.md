pytracker
=========

A python package for interacting with a webcam for gaze tracking &amp; pupillometry

Example usage:

    if __name__ == '__main__':
        import pytracker
        import time
        camIndex = 1
        camRes = [1920,1080]
        previewDownsize = 2
        numWorkers = 0
        timestampMethod = 0
        tracker = pytracker.trackerClass(camIndex=camIndex,camRes=camRes,numWorkers=numWorkers,previewDownsize=previewDownsize,timestampMethod=timestampMethod)
        tracker.start()
        while True:
            time.sleep(1)
            if not tracker.qFrom.empty():
                message = tracker.qFrom.get()
                if message=='done':
                    break

