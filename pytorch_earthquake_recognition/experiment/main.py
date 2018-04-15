import matplotlib
matplotlib.use('agg')
matplotlib.interactive(False)

import torch
from torch import nn
import torch.optim as optim
from torch.autograd import Variable
from torch.utils.data import DataLoader
from loaders.single_loader import SpectrogramSingleDataset
import models
import os
from datetime import datetime
import config
from utils import Evaluator
from writer_util import MySummaryWriter as SummaryWriter
from config import Folders


# Train and test
IMG_PATH = os.path.join(os.getcwd(), 'data/spectrograms')
BATCH_SIZE = 8   # 128
NUM_CLASSES = 2


# Neural Net Model
NET = models.mnist_one_component
MODEL_PATH = f'checkpoints/{NET.__name__}'

# Visualize
path = os.path.join(os.path.join(config.VISUALIZE_PATH, f'runs/{NET.__name__}/trial-{datetime.now()}'))
writer = SummaryWriter(path)

# Ignore Paths
ignore = Folders.values()
ignore_test = Folders.values()

ignore.remove(Folders.Oklahoma.value)
ignore_test.remove(Folders.Oklahoma.value)

iterations = 0

test_split = config.DIVIDE_TEST

# Applies in the order: 1. resize  2. crop
crop = resize = False
resize = (217, 316)   # (height, width)
crop = (217, 217)     # (height, width)


dataset_train = SpectrogramSingleDataset(IMG_PATH,
                                           transform=NET.transformations['train'],
                                           crop=crop,  # Will be random horizontal crop in the loader
                                           resize=resize,
                                           ignore=ignore,
                                           divide_test=test_split
                                           )

dataset_test = SpectrogramSingleDataset(IMG_PATH,
                                          transform=NET.transformations['test'],
                                          crop=crop,   # Will be center crop in the loader
                                          resize=resize,
                                          ignore=ignore_test,
                                          divide_test=test_split,
                                          test=True
                                          )
# Data Loaders
loader_args = dict(
                   batch_size=BATCH_SIZE,
                   num_workers=5,
                   pin_memory=True,
                   drop_last=True
                   )

train_loader = DataLoader(dataset_train, shuffle=True, **loader_args)
train_test_loader = DataLoader(dataset_train, shuffle=True, **loader_args)
test_loader = DataLoader(dataset_test, **loader_args)

# Setup Net
net = NET().cuda()
optimizer = optim.Adam(net.parameters())
criterion = nn.CrossEntropyLoss().cuda()


def guess_labels(batches):
    """
    Tries to guess labels based on data
    """
    dataiter = iter(test_loader)

    for i in range(batches):
        image, labels = dataiter.next()
        image = Variable(image).cuda()
        print('GroundTruth: ', ' '.join('%5s' % labels[j] for j in range(BATCH_SIZE)))
        outputs = net(image)
        _, predicted = torch.max(outputs.data, 1)
        print('Predicted:   ', ' '.join('%5s' % predicted[j] for j in range(BATCH_SIZE)))
        print()


def evaluate(net, data_loader, copy_net=False):
    """
    :param net:
    :param copy_net:
    :param data_loader:
    :return: Data structure containing the amount correct for each class
    """
    if copy_net:
        Net = NET().cuda()
        Net.load_state_dict(net.state_dict())
        Net.eval()
    else:
        Net = net

    eval = Evaluator()
    class_correct = [0 for _ in range(NUM_CLASSES)]
    class_total = [0 for _ in range(NUM_CLASSES)]

    for (inputs, labels) in data_loader:
        inputs, labels = Variable(inputs).cuda(), labels.cuda()
        outputs = Net(inputs)
        _, predicted = torch.max(outputs.data, 1)
        guesses = (predicted == labels).squeeze()

        # label: int, 0 to len(NUM_CLASSES)
        # guess: int, 0 or 1 (i.e. True or False)
        for guess, label in zip(guesses, labels):
            class_correct[label] += guess
            class_total[label] += 1

    # Update the information in the Evaluator
    for i, (correct, total) in enumerate(zip(class_correct, class_total)):
        eval.update_accuracy(class_name=i, amount_correct=correct, amount_total=total)

    return eval


def save_model(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    torch.save(net.state_dict(), path)


def load_model(path):
    return net.load_state_dict(torch.load(path))


def print_evaluation(evaluator, description):
    correct = 100 * evaluator.total_percent_correct()
    print('Accuracy of the network on %s images: %d %%' % (description, correct))

    for name, info in evaluator.class_info.items():
        print('Accuracy of the network on %s class  %s: [%2d / %2d] %2d %%' % (description, name,
                                                                               info.amount_correct,
                                                                               info.amount_total,
                                                                               evaluator.percent_correct(name) * 100))

def test(net, loader, copy_net=False):
    """
    :param net: the net to test on
    :param copy_net: boolean, whether to copy the net (if in the middle of training, you won't want to use the current net)
    """
    evaluator = evaluate(net, data_loader=loader, copy_net=copy_net)
    return evaluator


def write_images():
    """
    :return:
    """
    # Write Images
    noise_index = next(dataset_train.get_next_index_with_label(0))
    local_index = next(dataset_train.get_next_index_with_label(1))

    noise_raw = dataset_train.preview_raw(noise_index, show=False)
    img1 = writer.figure_to_image(noise_raw)

    noise_transformed = dataset_train.preview(noise_index, show=False)
    img2 = writer.figure_to_image(noise_transformed)

    local_raw = dataset_train.preview_raw(local_index, show=False)
    img3 = writer.figure_to_image(local_raw)

    local_transformed = dataset_train.preview(local_index, show=False)
    img4 = writer.figure_to_image(local_transformed)

    noise_image = writer.combine_images_horizontal([img1, img2])
    local_image = writer.combine_images_horizontal([img3, img4])

    image = writer.combine_images_vertical([noise_image, local_image])
    writer.add_pil_image('Transformations', image)


def write_info():
    transforms = ['Resize: ' + str(resize), 'Crop: ' + str(crop)]
    step = 0

    for transformation in transforms + NET._train + NET._transformations:
        writer.add_text('Transformations_Train', str(transformation), global_step=step)
        step += 1

    step = 0
    for transformation in transforms + NET._test + NET._transformations:
        writer.add_text('Transformations_Test', str(transformation), global_step=step)
        step += 1

def train(epoch):
    global iterations
    running_loss = 0.0

    for i, (true_inputs, true_labels) in enumerate(train_loader, 0):
        # wrap them in Variable
        inputs, labels = [Variable(input).cuda() for input in true_inputs], Variable(true_labels).cuda()

        # zero the parameter gradients
        optimizer.zero_grad()

        # forward + backward + optimize
        outputs = net(inputs)

        # Compute the loss
        loss = criterion(outputs, labels)

        # backpropagate and update optimizer learning rate
        loss.backward()
        optimizer.step()

        running_loss += loss.data[0]

        def print_loss():
            print('Train Epoch: {} [{}/{} ({:.0f}%)]\tLoss: {:.6f}'.format(
                  epoch,
                  int(i * len(true_inputs) * BATCH_SIZE / 3),
                  len(train_loader) * BATCH_SIZE,
                  100. * i / len(train_loader),
                  loss.data[0]))

            writer.add_scalar('train_loss', loss.data[0], iterations)

        def test_loss():
            test_evaluator = evaluate(net, test_loader, copy_net=True)
            train_evaluator = evaluate(net, train_test_loader, copy_net=True)

            print()
            print_evaluation(test_evaluator, 'test')
            print()
            print_evaluation(train_evaluator, 'train')
            print()

            percent_correct = lambda evaluator: evaluator.total_percent_correct() * 100
            writer.add_scalars('amount_correct',
                               {'test_amount_correct': percent_correct(test_evaluator),
                                'train_amount_correct': percent_correct(train_evaluator)},
                               epoch)

            writer.add_scalars('test_class_correct',
                               {'test_noise': test_evaluator.percent_correct(0),
                                'test_local': test_evaluator.percent_correct(1)},
                               epoch)

        def write_model():
            path = f'./checkpoints/{NET.__name__}/model{epoch}.pt'
            save_model(path)

        if iterations % 1000 == 0:
            print_loss()

        if epoch % 3 == 0 and i == 0:
            test_loss()

        if epoch % 10 == 0 and i == 0:
            write_model()

        iterations += BATCH_SIZE



if __name__ == '__main__':
    print("Writing Info")
    write_info()
    write_images()

    def train_net(epochs):
        for epoch in range(epochs):
            train(epoch)

    train_net(100)

    #########################

    def load_net():
        path = f'./checkpoints/{NET.__name__}/model40.pt'
        load_model(path)
        net.eval()

    load_net()
    evaluate(net, test_loader, copy_net=False)
    guess_labels(1)

    pass

