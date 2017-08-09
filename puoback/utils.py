import time


class Progress_indicator:
    def __init__(self, max):
        self.curr = 0
        self.max = max
        self.report_interval = max/20
        self.start_time = time.time()

    def tick(self):
        self.curr += 1
        if self.curr % self.report_interval == 1:
            percent_info = str((100 * self.curr / self.max)) + '%'
            time_info = " (" + str(int(time.time() - self.start_time)) + " seconds worked so far)"
            print "Progress at " + percent_info + time_info
