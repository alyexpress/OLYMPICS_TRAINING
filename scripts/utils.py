import hashlib
import matplotlib.pyplot as plt


def hashed(data):
    return hashlib.md5((data + "92vALen3n").encode()).hexdigest()


def progress(values, id):
    res = [0]
    for v in values: res.append(res[-1] + v)
    plt.figure(figsize=(20, 4))
    plt.plot(range(len(res)), res,
             color="black", linewidth=4)
    plt.axis(False)
    plt.grid(True)
    plt.savefig(f"static/imgs/progress/{id}.png")


def elo(rating1, rating2, res):
    E1 = 1 / (1 + 10 ** ((rating2 - rating1) / 400))
    E2 = 1 / (1 + 10 ** ((rating1 - rating2) / 400))
    print(E1, E2)
    rating1 += 32 * (res - E1)
    rating2 += 32 * ((1 - res) - E2)
    return round(rating1), round(rating2)
