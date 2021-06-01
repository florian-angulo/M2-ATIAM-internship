# -*- coding: utf-8 -*-

import random
from tqdm import tqdm
import glob
import torch
import torch.optim as optim
from torch.utils.data import DataLoader
from torch.utils.tensorboard import SummaryWriter
from dataloader import CQTsDataset
from utils import triplet_loss
from model import ConvNet
from online_triplet_loss.losses import *

print('libraries imported')

device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
root_path = "/tsi/clusterhome/atiam-1005/music-structure-estimation/simple_supervised/"
data_path_harmonix = "/tsi/clusterhome/atiam-1005/data/Harmonix/cqts/*"
data_path_harmonix2 = "/tsi/clusterhome/atiam-1005/data/Harmonix/cqts_to_check/*"
data_path_personal = "/tsi/clusterhome/atiam-1005/data/Personal/cqts/*"
data_path_isoph = "/tsi/clusterhome/atiam-1005/data/Harmonix/cqts/*"

writer = SummaryWriter(root_path + "runs/unsupervised_harmo_isoph_personal_biased")


N_EPOCH = 250
batch_size = 6
n_batchs = 256
n_triplets = 16
dim_cqts = (72, 64)
n_files_train = glob.glob(data_path_harmonix)
n_files_train.extend(glob.glob(data_path_harmonix2))
n_files_train.extend(glob.glob(data_path_personal))
n_files_val = glob.glob(data_path_isoph)


val_dataset = CQTsDataset(n_files_val, n_triplets)


print(len(n_files_train), 'training examples')
print(len(n_files_val), 'validation examples')

model = ConvNet().to(device)
optimizer = optim.Adam(model.parameters())

for epoch in range(N_EPOCH):
    running_loss = 0.0
    random.shuffle(n_files_train)
    train_dataset = CQTsDataset(n_files_train[:batch_size*n_batchs], path_beats, path_labels, n_triplets)
    train_loader = DataLoader(
          dataset=train_dataset,
          batch_size=batch_size,
          num_workers = 6
          )

    model.train()
    print("EPOCH " + str(epoch + 1) + "/" + str(N_EPOCH))
    for i, data in enumerate(tqdm(train_loader)):
        # data = data.view(-1, 72, 512).to(device)
        # zero the parameter gradients
        optimizer.zero_grad()
        # forward + backward + optimize
        train_loss = 0
        for k in range(batch_size):
            embeddings = model(data[k][0])
            loss, _ += batch_all_triplet_loss(data[k][1], embeddings, margin=0.1)
            train_loss += loss
        train_loss.backward()
        optimizer.step()
        running_loss += train_loss.item()
    # print statistics
    print('average train loss: %.6f' %
                (running_loss/len(train_loader)))
    # ...log the running loss
    writer.add_scalar('training loss',
                    running_loss / len(train_loader),
                    epoch)



    with torch.no_grad():
        model.eval()
        running_loss = 0.0
        validation_loader = DataLoader(
            dataset=val_dataset,
            batch_size=batch_size,
            num_workers = 6
        )
        for i, data in enumerate(tqdm(validation_loader)):
            # data = data.view(-1, 72, 512).to(device)
            # zero the parameter gradients
            optimizer.zero_grad()
            # forward + backward + optimize
            train_loss = 0
            for k in range(batch_size):
                embeddings = model(data[k][0])
                loss, _ += batch_all_triplet_loss(data[k][1], embeddings, margin=0.1)
                train_loss += loss
            train_loss.backward()
            optimizer.step()
            running_loss += train_loss.item()
        # print statistics
        print('average validation loss (Isophonics): %.6f' %
              (running_loss / len(validation_loader)))
        # ...log the running loss
        writer.add_scalar('validation loss (Isophonics)',
                          running_loss / len(validation_loader),
                          epoch)

    if epoch % 10 == 9:
        torch.save(model.state_dict(), root_path + "weights_biased_sampling/model" + str(epoch) + ".pt")
print('Finished Training')
