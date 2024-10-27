import psutil
from collections import deque
import time
import threading
import logging
import queue
import matplotlib.pyplot as plt

logging.basicConfig(
    format="%(asctime)s (%(threadName)s): %(message)s",
    level=logging.INFO,
    datefmt="%H:%M:%S")

class CPUUtilization(threading.Thread):
    def __init__(self, event, data, name=None):
        super().__init__(name=name)
        self.event = event
        self.logger = logging.getLogger()
        self.data = data
        self.start_time = time.time()

    def run(self):
        cpu_percent = psutil.cpu_percent(interval=None)
        while not self.event.is_set():
            try:
                timestamp = time.time() - self.start_time
                cpu_percent = psutil.cpu_percent(interval=None)
                self.logger.debug(f"{timestamp}, {cpu_percent}%")
                self.data.put((timestamp, cpu_percent))
                time.sleep(.1)
            except Exception as e:
                self.logger.error(e)
        return
    
class ProcessData(threading.Thread):
    def __init__(self, event, input_data, output, name=None):
        super().__init__(name=name)
        self.logger = logging.getLogger()
        self.event = event
        self.samples = deque([])
        self.data = input_data
        self.processed_data = output

    def run(self):
        num_sample_avg = int(1/0.015) * 0.5
        sum = 0
        while not self.event.is_set():
            try:
                timestamp, data = self.data.get(timeout=1)
                self.logger.debug(f"{timestamp}, {data} %")
                if len(self.samples) <= num_sample_avg:
                   sum += data
                   self.samples.append(data)
                   self.processed_data.put((timestamp, 0))
                else:
                    if len(self.samples) > 0:
                        sum = sum - self.samples.popleft() + data
                        mean = sum / len(self.samples)
                        self.processed_data.put((timestamp, mean))
                    self.samples.append(data)
            except Exception as e:
                self.logger.error(f"Error {e}")

class Plotter(threading.Thread):
    def __init__(self, event, data, name=None):
        super().__init__(name=name)
        self.logger = logging.getLogger()
        self.event = event
        self.data = data
        
        self.fig = plt.figure()
        self.ax = self.fig.add_subplot(1,1,1)
        self.x = deque([])
        self.y = deque([])
        self.ax.set_yticks([10*i for i in range(0,11)])
        self.ax.set_ylim(0,100)
        self.ax.grid()
        self.ax.set_xlabel("Time Elapsed [s]")
        self.ax.set_ylabel("CPU Utilization [%]")
        self.line = self.ax.plot([],[])[0]
        self.fill = self.ax.fill_between([],[])

    def run(self):
        while not self.event.is_set():
            try:
                timestamp, data = self.data.get(timeout=1)
                self.logger.debug(f"{timestamp}, {data} %")
                self.x.append(timestamp)
                self.y.append(data)

                if len(self.x) > 2:
                    if self.x[-1] - self.x[0] >= 60:
                        self.y.popleft()
                        self.x.popleft() 
                        #num_samp = int(60/(self.x[-1] - self.x[-2]))
                        #self.ax.set_xlim(self.x[-num_samp],self.x[-1])

                self.line.remove()
                self.fill.remove()
                self.line = self.ax.plot(self.x, self.y, color="tab:blue")[0]
                self.fill = self.ax.fill_between(self.x, self.y, color="lightblue")
                self.ax.relim()
                self.logger.info(f"num lines: {len(plt.gca().lines)}")
                self.fig.canvas.draw()
                self.fig.canvas.flush_events()
            except Exception as e:
                self.logger.debug(f"Error: {e}: could not plot")

        return
        
if __name__ == "__main__":
    event = threading.Event()
    data = queue.Queue()
    processed_data = queue.Queue()
    try:
        process_thread = ProcessData(event, data, processed_data, name="Process Data Thread")
        plotter_thread = Plotter(event, processed_data, name="Plotter Thread")
        cpu_thread = CPUUtilization(event, data, name="CPUUtilization Thread")
        process_thread.start()
        cpu_thread.start()
        plotter_thread.start()
        plt.show()
        while not event.is_set():
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Exiting")
        data.shutdown()
        processed_data.shutdown()
        event.set()
        cpu_thread.join()
        plotter_thread.join()
