'''Train CIFAR10 with PyTorch.'''
from __future__ import print_function

import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
import torch.backends.cudnn as cudnn
from torchsummary import summary

import torchvision
import torchvision.transforms as transforms

import os
import cv2
import argparse

from models import *
from utils import progress_bar
import numpy as np

import matplotlib.pyplot as plt

parser = argparse.ArgumentParser(description='PyTorch CIFAR10 Training')
parser.add_argument('--lr', default=0.1, type=float, help='learning rate')
parser.add_argument('--resume', '-r', help='resume from checkpoint',
                    default='../checkpoint/resnet101_1_1_ckpt.t8')
args = parser.parse_args()

device = 'cuda' if torch.cuda.is_available() else 'cpu'

best_acc = 0  # best test accuracy
start_epoch = 0  # start from epoch 0 or last checkpoint epoch

# Data
print('==> Preparing data..')
transform_train = transforms.Compose([
    transforms.RandomCrop(32, padding=4),
    transforms.RandomHorizontalFlip(),
    transforms.ToTensor(),
    transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2023, 0.1994, 0.2010)),
])

transform_test = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2023, 0.1994, 0.2010)),
])

trainset = torchvision.datasets.CIFAR10(root='../data', train=True, download=True, transform=transform_train)
trainloader = torch.utils.data.DataLoader(trainset, batch_size=128, shuffle=True, num_workers=2)

testset = torchvision.datasets.CIFAR10(root='../data', train=False, download=True, transform=transform_test)
testloader = torch.utils.data.DataLoader(testset, batch_size=100, shuffle=False, num_workers=2)

classes = ('plane', 'car', 'bird', 'cat', 'deer', 'dog', 'frog', 'horse', 'ship', 'truck')

# Model
print('==> Building model..')
# net = VGG('VGG19')
# net = ResNet18()
# net = PreActResNet18()
# net = GoogLeNet()
# net = DenseNet121()
# net = ResNeXt29_2x64d()
# net = MobileNet()
# net = MobileNetV2()
# net = DPN92()
# net = ShuffleNetG2()
# net = SENet18()
# net = ShuffleNetV2(1)
net = ResNet101()

#net = VGG('VGG19')

net = net.to(device)
if device == 'cuda':
    net = torch.nn.DataParallel(net)
    cudnn.benchmark = True

if args.resume:
    # Load checkpoint.
    print('==> Resuming from checkpoint..')
    assert os.path.isdir('../checkpoint'), 'Error: no checkpoint directory found!'
    checkpoint = torch.load(args.resume)
    net.load_state_dict(checkpoint['net'])
    best_acc = checkpoint['acc']
    start_epoch = checkpoint['epoch']

#summary(net, (3, 32, 32))
#exit(1)

criterion = nn.CrossEntropyLoss()
optimizer = optim.SGD(net.parameters(), lr=args.lr, momentum=0.9, weight_decay=5e-4)


# for name in net.parameters():
#     print(name)


# Training
def train(epoch):
    print('\nEpoch: %d' % epoch)
    net.train()
    train_loss = 0
    correct = 0
    total = 0
    for batch_idx, (inputs, targets) in enumerate(trainloader):
        inputs, targets = inputs.to(device), targets.to(device)
        optimizer.zero_grad()
        outputs = net(inputs)
        loss = criterion(outputs, targets)
        loss.backward()
        optimizer.step()

        train_loss += loss.item()
        _, predicted = outputs.max(1)
        total += targets.size(0)
        correct += predicted.eq(targets).sum().item()

        progress_bar(batch_idx, len(trainloader), 'Loss: %.3f | Acc: %.3f%% (%d/%d)'
                     % (train_loss / (batch_idx + 1), 100. * correct / total, correct, total))


def test(epoch):
    global best_acc
    net.eval()
    test_loss = 0
    correct = 0
    total = 0
    with torch.no_grad():
        for batch_idx, (inputs, targets) in enumerate(testloader):
            inputs, targets = inputs.to(device), targets.to(device)
            outputs = net(inputs)
            loss = criterion(outputs, targets)

            test_loss += loss.item()
            _, predicted = outputs.max(1)
            total += targets.size(0)
            correct += predicted.eq(targets).sum().item()

            progress_bar(batch_idx, len(testloader), 'Loss: %.3f | Acc: %.3f%% (%d/%d)'
                         % (test_loss / (batch_idx + 1), 100. * correct / total, correct, total))

    # Save checkpoint.
    acc = 100. * correct / total
    if acc > best_acc:
        print('Saving..')
        state = {
            'net': net.state_dict(),
            'acc': acc,
            'epoch': epoch,
        }
        if not os.path.isdir('../checkpoint'):
            os.mkdir('../checkpoint')
        torch.save(state, '../checkpoint/ckpt.t7')
        best_acc = acc

def show_batch(batch):
    # im = torchvision.utils.make_grid(batch)
    # #print(im.shape)
    # plt.imshow(np.transpose(im.numpy(), (1, 2, 0)))
    # # print(im.numpy().shape)
    # # print(np.transpose(im.numpy(), (1, 2, 0)).shape)
    # # plt.imshow(np.transpose(im.numpy(), (1, 2, 0)))
    # plt.show()

    if not os.path.exists('visualized_imgs'):
        os.mkdir('visualized_imgs')

    batch_data = batch.detach().cpu().numpy()
    for sample_i in range(batch_data.shape[0]):
        if not os.path.exists(os.path.join('visualized_imgs', str(sample_i))):
            os.mkdir(os.path.join('visualized_imgs', str(sample_i)))
        for channel_c in range( batch_data.shape[1] ):
            raw_data = batch_data[sample_i, channel_c]
            img_data = np.zeros((raw_data.shape[1], raw_data.shape[2], 3), dtype=np.uint8)
            for i in range(3):
                raw_data_i = raw_data[i, :, :]
                raw_data_i = (raw_data_i - np.min(raw_data_i)) / (np.max(raw_data_i) - np.min(raw_data_i)) * 255
                img_data[:, :, i] = np.uint8(raw_data_i)
            cv2.imwrite(os.path.join('visualized_imgs', str(sample_i), str(channel_c) + '.png'), img_data)


def extract_features(mode):
    # FIXME: what is top-k?
    table = np.load('../results/topk.npy')
    #print(table.shape)
    #exit(1)
    trainset = torchvision.datasets.CIFAR10(root='../data', train=True, download=True, transform=transform_train)
    trainloader = torch.utils.data.DataLoader(trainset, batch_size=100, shuffle=True, num_workers=2)

    testset = torchvision.datasets.CIFAR10(root='../data', train=False, download=True, transform=transform_test)
    testloader = torch.utils.data.DataLoader(testset, batch_size=2, shuffle=False, num_workers=2)

    loader = {'train': trainloader, 'test': testloader}[mode]

    with torch.no_grad():
        for batch_idx, (inputs, targets) in enumerate(loader):

            #print(inputs[0])

            #show_batch(inputs[0:200])
            #exit(1)

            inputs, targets = inputs.to(device), targets.to(device)
            outputs = net.module.forward_cam(inputs)[4]

            #print(outputs[1,11,:])
            #exit(1)

            list_outputs = []
            print(targets.data)

            for i, output in enumerate(outputs):
                print(i, targets[i].data, table[targets[i]])
                features = output[table[targets[i]]]

                list_outputs.append(features)

            features = torch.stack(list_outputs)

            # FIXME: check output with pdb.trace
            max_features = F.adaptive_max_pool2d(features, 1)
            features = features / (max_features + 1e-16)  # this is the attention maps

            features_ = F.interpolate(features, inputs.shape[-2:], mode='bilinear', align_corners=False)

            mask = torch.where(features_ > 0.5, torch.ones_like(features_), torch.zeros_like(features_))

            masked_inputs = inputs.unsqueeze(1) * mask.unsqueeze(2)

            show_batch(masked_inputs)
            exit(1)

            list_masked_outputs = []

            for i, masked_input in enumerate(masked_inputs):
                masked_output = net(masked_input).squeeze()

                list_masked_outputs.append(masked_output)

            masked_outputs = torch.stack(
                list_masked_outputs)  # this is the feature output w.r.t the highest frequency features of that class


if __name__ == '__main__':
    extract_features('train')
    # extract_features('val')
    #extract_features('test')

    # for epoch in range(start_epoch, start_epoch+200):
    #     train(epoch)
    #     test(epoch)
