from pytorch_utils.utils import evaluate, write_images, load_model, print_evaluation, write_info, train
import models
import copy
import torch.nn as nn
from main import *

NET = models.mnist_three_component_exp

 # Load Net


models = [
        ('everywhere97percent-nobenz-crop-.7-width', 'iterations-5205248-total-96.79-class0-96.04-class1-98.13.pt'),
        ('everywhere-97percent-nobenz', 'iterations-6778880-total-97.73-class0-97.3-class1-98.49.pt'),
        ('99%-(no-benz)', 'iterations-17336960-total-98.95-class0-98.75-class1-99.31.pt'),
        ('99%-(no-benz)', 'iterations-18476800-total-99.08-class0-99.08-class1-99.09.pt')

]

model_chosen = models[2]
model_path = model_chosen[0]
model_name = model_chosen[1]
CHECKPOINT_PATH = f'./visualize/saved/2019/{NET.__name__}/{model_path}/checkpoints/{model_name}'

# Use existing model
def load_net(checkpoint_path):
        print("Loading Net")
        net = NET().cuda()

        checkpoint = torch.load(CHECKPOINT_PATH)

        net.load_state_dict(checkpoint['model_state_dict'])
        optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        loss = checkpoint['loss']
        print("Loaded", checkpoint['name'])
        net.train()
        return net


def replace_model(net, size=32):
    net.classifier =  nn.Sequential(
            nn.Linear(4800, size, bias=False),
            nn.BatchNorm1d(size),
            nn.ReLU(inplace=True),
            nn.Dropout(0.5),

            nn.Linear(size, size, bias=False),
            nn.BatchNorm1d(size),
            nn.ReLU(inplace=True),
            nn.Dropout(0.5),
 
            nn.Linear(size, 2)
        )
    


# Freeze convolutional parameters
def freeze_parameters(net):
    for param in net.feats.parameters():
        param.requires_grad = False


# Set up loaders
def make_loader(samples, ratio, test=False):
    dataset = dataset_test if test else dataset_train
    dataset = subsample_dataset(dataset, samples, ratio)

    if test:
        loader = DataLoader(dataset,
                            **loader_args)

    else:
        train_sampler = utils.make_weighted_sampler(dataset, NUM_CLASSES, weigh_classes=[1, 4])
        loader = DataLoader(dataset,
                            shuffle=not train_sampler,
                            sampler=train_sampler,
                            **loader_args)
    return loader


# Train on new data
def train_net(epochs):
    best = None
    for epoch in range(epochs):
        evaluator = train(epoch + 1, train_loader, test_loader, optimizer, criterion, net, writer,
              write=True,
              checkpoint_path=checkpoint_path,
              print_loss_every=1000,
              print_test_evaluation_every=10000)

        if best is None:
            best = evaluator
        elif evaluator.normalized_percent_correct(weigh_events=1.1) >= best.normalized_percent_correct(weigh_events=1.1):
            best = evaluator

    return best



# Initial Results before Transfer Learning
# print("Testing Net -- Initial")
# test_evaluator = evaluate(net, test_loader, copy_net=True)
# print()
# print_evaluation(test_evaluator, 'test')

# Train it
feed_forward_size = 64
ratio = {0: 1, 1: 1}
test_loader = make_loader(1000, ratio, test=True)

samples = [1,   10,  50,  100, 200, 500, 1000, 2000, 4000, 8000, 16000, 32000, 64000, 128000]
epochs =  [2000, 1000, 1000, 500,  500,  500,  200,   200,   200,   100,   100,    50,    20,    20]
results = {}
for sample, epoch in zip(samples, epochs):
    train_loader = make_loader(sample, ratio, test=False)

    net = load_net(CHECKPOINT_PATH)
    replace_model(net, feed_forward_size)
    net.cuda()
    optimizer = optim.Adam(net.parameters())
    criterion = nn.CrossEntropyLoss().cuda()
    freeze_parameters(net)

    evaluator = train_net(epoch)
    results[sample] = evaluator

from pprint import pprint
pprint(results)
