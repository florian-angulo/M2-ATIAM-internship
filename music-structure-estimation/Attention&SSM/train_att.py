# -*- coding: utf-8 -*-

import random
from tqdm import tqdm
import glob
import torch
import torch.optim as optim
from torch.utils.data import DataLoader
from torch.utils.tensorboard import SummaryWriter
from dataloader import CQTsDataset
from model import SSMnet
from utils import weighted_bce_loss

print('libraries imported')

device = torch.device("cuda:0" if torch.cuda.is_available() else "error")
root_path = "/tsi/clusterhome/atiam-1005/M2-ATIAM-internship/music-structure-estimation/Attention&SSM/"
data_path_harmonix = "/tsi/clusterhome/atiam-1005/data/Harmonix/cqts/*"
data_path_isoph = "/tsi/clusterhome/atiam-1005/data/Isophonics/cqts/*"

name_exp = "from_less_fc_att&context1e-3_freeze_relu_softmax_normalized"
writer = SummaryWriter('{0}runs/{1}'.format(root_path, name_exp))


N_EPOCH = 250
batch_size = 1
backward_size = 6

files_train = glob.glob(data_path_harmonix)
files_val = glob.glob(data_path_isoph)

val_dataset = CQTsDataset(files_val)
validation_loader = DataLoader(
    dataset=val_dataset,
    batch_size=batch_size,
)

print(len(files_train), 'training examples')
print(len(files_val), 'validation examples')

model = SSMnet().to(device)

optimizer = optim.Adam(model.parameters(),lr=1e-3)
scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, 'min')

best_loss = float('inf')

model.load_state_dict(torch.load('{0}weights/pretrain_less_fc_last.pt'.format(root_path)), strict=False)


for epoch in range(N_EPOCH):
    running_loss = 0.0
    running_loss_context = 0.0
    #running_reg = 0.0
    random.shuffle(files_train)
    train_dataset = CQTsDataset(files_train)
    train_loader = DataLoader(
          dataset=train_dataset,
          batch_size=batch_size,
          )
    model.train()
    print("EPOCH " + str(epoch + 1) + "/" + str(N_EPOCH))
    for i, (cqts, ssm) in enumerate(tqdm(train_loader)):
        ssm_hat, att_scores = model(cqts)
        maxi_att = torch.max(att_scores, axis=1)[0]
        att_scores = att_scores/maxi_att[:,:,None]
        
        _, train_loss = weighted_bce_loss(att_scores, ssm)
        train_loss /= backward_size
        _, loss_context = weighted_bce_loss(ssm_hat, ssm)
        loss_context /= backward_size
        loss_context.backward(retain_graph=True)
        train_loss.backward(retain_graph=True)
        running_loss += train_loss.item() * backward_size
        running_loss_context += loss_context.item() * backward_size
        #running_reg += (loss_reg.item() - train_loss.item()) 
        if (i + 1) % backward_size == 0:
            optimizer.step()
            optimizer.zero_grad()
    
    optimizer.step()
    optimizer.zero_grad()
    
    # print statistics
    print('average train loss: %.6f' %
                (running_loss/len(train_loader)))
    print('average train loss context (Isophonics): %.6f' %
              (running_loss_context / len(validation_loader)))
    # ...log the running loss
    writer.add_scalar('training loss',
                    running_loss / len(train_loader),
                    epoch)



    with torch.no_grad():
        model.eval()
        running_loss = 0.0
        running_loss_context = 0.0
        for i, (cqts, ssm) in enumerate(tqdm(validation_loader)):
            ssm_hat, att_scores = model(cqts)
            maxi_att = torch.max(att_scores, axis=1)[0]
            att_scores = att_scores/maxi_att[:,:,None]
            _, val_loss = weighted_bce_loss(att_scores, ssm)
            _, loss_context = weighted_bce_loss(ssm_hat, ssm)
            running_loss += val_loss.item()
            running_loss_context += loss_context.item()
        # print statistics
        print('average validation loss (Isophonics): %.6f' %
              (running_loss / len(validation_loader)))
        print('average validation loss context (Isophonics): %.6f' %
              (running_loss_context / len(validation_loader)))
        # ...log the running loss
        writer.add_scalar('validation loss (Isophonics)',
                          running_loss / len(validation_loader),
                          epoch)

    scheduler.step(running_loss)
    # Save best model if validation loss is improved and update regularly last model state
    if running_loss <= best_loss:
        torch.save(model.state_dict(), "{0}weights/{1}_best.pt".format(root_path, name_exp))
        best_loss = running_loss
    
    torch.save(model.state_dict(), "{0}weights/{1}_last.pt".format(root_path, name_exp))
        
print('Finished Training')