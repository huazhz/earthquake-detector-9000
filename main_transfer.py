from pytorch_utils.utils import evaluate, write_images, load_model, print_evaluation, write_info, train, load_checkpoint, train_best_model, train_sample_sizes
import models
import copy
import torch.nn as nn
from main import *
from main import _main_make_datasets, _main_make_loaders

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


dataset_train, dataset_test = _main_make_datasets()
dataset_train.shuffle()
dataset_test.shuffle()

net, optimizer, criterion = create_model()

# Use existing model
def load_net(checkpoint_path):
        print("Loading Net")
        net = NET().cuda()
        load_checkpoint(checkpoint_path, net, optimizer)
        return net

def replace_model(net, size=32):
    net.classifier = nn.Sequential(
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


# Initial Results before Transfer Learning
# print("Testing Net -- Initial")
# test_evaluator = evaluate(net, test_loader, copy_net=True)
# print()
# print_evaluation(test_evaluator, 'test')

# Train it
feed_forward_size = 64

import math
samples = [10000,10,   10,   50,   100,  200,  500,  1000,   2000,  4000,  8000,  16000,  32000, 64000, 128000, 256000]
epochs =  [100,30,   30,   30,   30,   30,   30,   30,     30,    30,    30,    30,     20,    5,    3,      1]
results = {}



# Create a final test loader where it has unseen data
dataset_final = copy.deepcopy(dataset_train)
del dataset_final.file_paths[10000:]
del dataset_train.file_paths[:10000]

assert verify_dataset_integrity(dataset_train, dataset_final)

# IMPORTANT - CAN NOT USE WEIGHTED SAMPLER HERE
train_loader = create_loader(dataset_train, train=True)
test_loader = create_loader(dataset_test, train=False)
final_test_loader = DataLoader(dataset_final, **loader_args)

net = load_net(CHECKPOINT_PATH)
replace_model(net, feed_forward_size)
net.cuda()
net.train() 
optimizer = optim.Adam(net.parameters())
criterion = nn.CrossEntropyLoss().cuda()
freeze_parameters(net)

hyper_params = zip(samples, epochs)

results = train_sample_sizes(hyper_params, train_loader, test_loader, final_test_loader,
                             net, optimizer, criterion, 
                             writer=writer,
                             write=False,
                             print_loss_every=1_000,
                             print_test_evaluation_every=10_000,
                             yield_every = 10_000)


from pprint import pprint
print("The format is: Validation Results, epoch, validation percent correct, Test results, test percent correct")
pprint(results)
