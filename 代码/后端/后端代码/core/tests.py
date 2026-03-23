from django.test import TestCase

# Create your tests here.

import pickle
import matplotlib.pyplot as plt

if __name__ == "__main__":
    with open('result.pkl', 'rb') as f:
        result = pickle.load(f)
        print()

        img = result[1][1]
        img = result[3][1]
        img = result[4][1][0]
        img = img.astype('uint8')
        print(img.shape)

        plt.imshow(img)#, cmap='gray')  # 不指定 cmap 时默认是 viridis，这里用 gray 更直观
        plt.axis('off')  # 关闭坐标轴
        plt.show()

        # 按照原尺寸保存图片
        plt.imsave('test.png', img)