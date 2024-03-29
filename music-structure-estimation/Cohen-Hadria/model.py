import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim

from torch_same_pad import get_pad

class ConvNet(nn.Module):
    def __init__(self, big_conv=False):
        super(ConvNet, self).__init__()
        kernel_conv1 = (12, 4) if big_conv else (6, 4)
        kernel_conv2 = (6, 4) if big_conv else (6, 4)
        kernel_conv3 = (3, 2) if big_conv else (6, 4)
        # kernels (12, 4) (6, 4) (3, 2)
        self.pad1 = get_pad((72, 64), kernel_conv1) 
        self.conv1 = nn.Conv2d(1, 32, kernel_conv1)
        self.bnc1 = nn.GroupNorm(32, 32)
        self.pool1 = nn.MaxPool2d(kernel_size=(2, 4))
        self.pad2 = get_pad((36, 16), kernel_conv2)
        self.conv2 = nn.Conv2d(32, 64, kernel_conv2)
        self.bnc2 = nn.GroupNorm(32, 64)
        self.pool2 = nn.MaxPool2d(kernel_size=(3, 4))
        self.pad3 = get_pad((12, 4), kernel_conv3)
        self.conv3 = nn.Conv2d(64, 128, kernel_conv3)
        self.bnc3 = nn.GroupNorm(32, 128)
        self.pool3 = nn.MaxPool2d(kernel_size=(3, 2))
        self.resize = 4 * 2 * 128
        self.fc1 = nn.Linear(self.resize, 128)
        self.selu = nn.SELU()
    
    def apply_cnn(self,x):
        #x = x.unsqueeze(1) # for 1 channel
        x = self.pool1(self.bnc1(self.selu(self.conv1(F.pad(x,self.pad1)))))
        x = self.pool2(self.bnc2(self.selu(self.conv2(F.pad(x,self.pad2)))))
        x = self.pool3(self.bnc3(self.selu(self.conv3(F.pad(x,self.pad3)))))
        x = x.view(-1, self.resize)
        x = F.normalize(self.selu(self.fc1(x)), p=2)
        return x

    def forward(self, x):
        a = self.apply_cnn(x[:, 0, :, :])
        p = self.apply_cnn(x[:, 1, :, :])
        n = self.apply_cnn(x[:, 2, :, :])

        return a, p, n

    def inference(self, x):
        return self.apply_cnn(x)
        
        
class CohenNet(nn.Module):
    def __init__(self, n_channels=1):
        super(CohenNet, self).__init__()
        kernel_conv1 = (4, 4)
        kernel_conv2 = (3, 3)
        #self.pad1 = get_pad((15, 15), kernel_conv) 
        self.conv1 = nn.Conv2d(n_channels, 32, kernel_conv1)
        self.bnc1 = nn.GroupNorm(32, 32)
        self.pool1 = nn.MaxPool2d(kernel_size=(2, 2))
        #self.pad2 = get_pad((6, 6), kernel_conv)
        self.conv2 = nn.Conv2d(32, 64, kernel_conv2)
        self.bnc2 = nn.GroupNorm(32, 64)
        self.pool2 = nn.MaxPool2d(kernel_size=(2, 2))
        self.resize = 2 * 2 * 64
        self.fc1 = nn.Linear(self.resize, 64)
        self.fc2 = nn.Linear(64, 1)
        self.selu = nn.SELU()

    def forward(self, x):
        x = x.unsqueeze(1)
        x = self.pool1(self.bnc1(self.selu(self.conv1(x))))
        x = self.pool2(self.bnc2(self.selu(self.conv2(x))))
        x = x.view(-1, self.resize)
        x = self.selu(self.fc1(x))
        x = torch.sigmoid(self.fc2(x))
        return x