import matplotlib.pyplot as plt
from collections import deque

a = deque([1,2,3,4,5])
b = deque([1,2,3,4,5])

line, = plt.plot(a,b)
collection = plt.fill_between(a,b, color="lightblue")

a.popleft()
b.popleft()

line.remove()
collection.remove()

plt.plot(a,b)
plt.fill_between(a,b, color="green")

plt.xlim(2,5)

plt.show()

