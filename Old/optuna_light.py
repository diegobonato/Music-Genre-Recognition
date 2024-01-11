import numpy as np
from torchvision.transforms import Compose, ToTensor
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader
import os 
from torch.optim import Adadelta
from tqdm import tqdm
import gc
import optuna
#import pytorch_lightning as pl
import lightning.pytorch as pl
from optuna.integration import PyTorchLightningPruningCallback
from utils_diego import readheavy, get_stft, clip_stft, DataDiego
import pickle

print("let's start")

##tensorboard --logdir=lightning_logs/ to visualize logs

class NNET2(nn.Module):
        
    def __init__(self):
        super(NNET2, self).__init__()
        
        
        self.c1 = nn.Sequential(
            nn.Conv2d(in_channels=1, out_channels=256,kernel_size=(4,513)),
            nn.BatchNorm2d(256),
            nn.ReLU()
        )

        self.c2 = nn.Sequential(
            nn.Conv2d(in_channels=256, out_channels=256, kernel_size=(4, 1),padding=(2,0)),
            nn.BatchNorm2d(256),
            nn.ReLU()
        )

        self.c3 = nn.Sequential(
            nn.Conv2d(in_channels=256, out_channels=256, kernel_size=(4, 1),padding=(1,0)),
            nn.BatchNorm2d(256),
            nn.ReLU()
        )
        
        self.fc = nn.Sequential(
            nn.Linear(256, 300),
            nn.ReLU(),
            nn.Linear(300, 150),
            nn.ReLU(),
            nn.Linear(150, 8),
            nn.Softmax(dim=1)
        )

        #self.apply(self._init_weights)
    """
    def _init_weights(self, module):
    
        if model_weights is None:
            if isinstance(module, torch.nn.Linear):
                torch.nn.init.xavier_uniform_(module.weight)
                if module.bias is not None:
                    module.bias.data.zero_()
            if isinstance(module, torch.nn.Conv2d):
                torch.nn.init.xavier_uniform_(module.weight)
                if module.bias is not None:
                    module.bias.data.zero_()
        else:
            ???
    """

    def forward(self,x):
        
        c1 = self.c1(x)
        c2 = self.c2(c1)
        c3 = self.c3(c2)
        x = c1 + c3
        max_pool = F.max_pool2d(x, kernel_size=(125,1))
        avg_pool = F.avg_pool2d(x, kernel_size=(125,1))
        x = max_pool + avg_pool
        x = self.fc(x.view(-1, 256))
        return x 


# Define a LightningModule (nn.Module subclass)
# A LightningModule defines a full system (ie: a GAN, autoencoder, BERT or a simple Image Classifier).
class LitNet(pl.LightningModule):
    
    def __init__(self, config: dict):
       
        super().__init__()
        # super(NNET2, self).__init__() ? 
        
        print('Network initialized')
        
        self.net = NNET2()
        self.val_loss = []
        self.train_loss = []
        self.best_val = np.inf
        self.config = config
        

    def forward(self,x):
        return self.net(x)

    # Training_step defines the training loop. 
    def training_step(self, batch, batch_idx=None):
        # training_step defines the train loop. It is independent of forward
        x_batch = batch[0]
        label_batch = batch[1]
        out = self.net(x_batch)
        loss = F.cross_entropy(out, label_batch) #Diego nota: aggiungere weights in base a distribuzione classi dataset?
        self.train_loss.append(loss.item())
        return loss

    def validation_step(self, batch, batch_idx=None):
        # validation_step defines the validation loop. It is independent of forward
        # When the validation_step() is called,
        # the model has been put in eval mode and PyTorch gradients have been disabled. 
        # At the end of validation, the model goes back to training mode and gradients are enabled.
        x_batch = batch[0]
        label_batch = batch[1]
        out = self.net(x_batch)
        loss = F.cross_entropy(out, label_batch)

        val_acc = np.sum(np.argmax(label_batch.detach().cpu().numpy(), axis=1) == np.argmax(out.detach().cpu().numpy(), axis=1)) / len(label_batch)

            
        #validation_loss = np.append(validation_loss,1 - val_acc)
        #print(f"accuracy: {val_acc*100} %")
        
        # Should I save the model based on loss or on accuracy?7
        """
        LitNet doesnt need to save the model, it is done automatically by pytorch lightning
        if loss.item() < self.best_val:
            print("Saved Model")
            torch.save(self.net.state_dict(), "saved_models/nnet2/model.pt")
            self.best_val = loss.item()
        """


        self.val_loss.append(loss.item())
        self.log("val_loss", loss.item(), prog_bar=True)
        self.log("val_acc", val_acc, prog_bar=True)

    def configure_optimizers(self):
        optimizer = Adadelta(self.net.parameters(), lr=self.config["lr"],rho=self.config["rho"], eps=self.config["eps"], weight_decay=self.config["weight_decay"])
        return optimizer
    

def import_and_preprocess_data(config: dict, test = False,n_train=1):
    
    if test:
        test = readheavy("test",2,"Audio/")
        test = get_stft(test)
        test_clip = clip_stft(test, 128)
        transforms = Compose([ ToTensor(), ])
        test_dataset = DataDiego(data=test_clip,transform=transforms)
        # Qui imposto una batch size arbitraria. Lo faccio perché  temo che la funzione di main mi dia problemi
        test_dataloader = DataLoader(test_dataset, 64, shuffle=False, num_workers=os.cpu_count())
        return test_dataloader
    print("reading train")
    #Convert Audio into stft data
    #train = readheavy("training",1,f"Audio/")
    
    train =  np.load(f"Audio/training_{n_train}.npy", allow_pickle = True)
    
    print("getting stft")
    train_stft = get_stft(train)
   
    del train
    gc.collect()

    valid = readheavy("validation",2,"Audio/")
    valid_stft = get_stft(valid)

    del valid
    gc.collect()

    # take each song and splits it into clips of n_samples 
    # creates 
    print("making clips")
    train_clip = clip_stft(train_stft, 128)
    print("making clips")
    valid_clip = clip_stft(valid_stft, 128)

    del train_stft
    del valid_stft

    gc.collect()

    transforms = Compose([ ToTensor(), ]) # Normalize(0,1) is not necessary for stft data

    train_dataset = DataDiego(data=train_clip,transform=transforms)
    valid_dataset = DataDiego(data=valid_clip,transform=transforms)

    del train_clip
    del valid_clip

    gc.collect()

    #Creation of dataloader classes
    batch_size = config["batch_size"]
    print("train dataloader")
    train_dataloader = DataLoader(train_dataset, batch_size, shuffle=True, num_workers=os.cpu_count())
    print("valid dataloader")
    valid_dataloader = DataLoader(valid_dataset, batch_size, shuffle=False, num_workers=os.cpu_count())
    print("data loaded")

    del train_dataset
    del valid_dataset
    gc.collect()

    return train_dataloader, valid_dataloader


def objective(trial):

    """
    # PyTorch Lightning will try to restore model parameters from previous trials if checkpoint
    # filenames match. Therefore, the filenames for each trial must be made unique.
    checkpoint_callback = pl.callbacks.ModelCheckpoint(
        os.path.join(MODEL_DIR, "trial_{}".format(trial.number)), monitor="accuracy"
    )

    """

    # Set the hyperparameters in the config dictionary
    hyperparameters = {
        "weight_decay": trial.suggest_float("weight_decay", 1e-6, 1e-3, log=True),
        "eps": trial.suggest_float("eps", 1e-10, 1e-5, log=True),
        "rho": trial.suggest_float("rho", 0.1, 0.9),
        "lr": trial.suggest_float("lr", 1e-4, 1e-2, log=True),
        "batch_size": trial.suggest_categorical("batch_size", [32, 64, 128])
    }

    trainer = pl.Trainer(max_epochs=100, check_val_every_n_epoch=10, log_every_n_steps=1, deterministic=True,
                        )
 # had to remove  early_stop_callback=PyTorchLightningPruningCallback(trial, monitor="val_loss") from trainer

    trainer.logger.log_hyperparams(hyperparameters)

    model = LitNet(hyperparameters)
   
    # Hard coding; we should find a way to iterate over the number of training sets
    n_train = 1
    train_dataloader, val_dataloader = import_and_preprocess_data(config=hyperparameters,n_train=n_train)
        
    trainer.fit(model, train_dataloader, val_dataloader)
    return trainer.callback_metrics["val_loss"].item()


def GridSearch():

    pruner = optuna.pruners.NopPruner()
    # print(pruner) <optuna.pruners._nop.NopPruner object at 0x7f4c2466ed50>
    # print(type(pruner)) <class 'optuna.pruners._nop.NopPruner'>

    study = optuna.create_study(study_name="myfirstoptimizationstudy", direction="minimize", pruner=pruner,storage="sqlite:///myfirstoptimizationstudy.db", load_if_exists=True)
    study.optimize(objective, n_trials=10, timeout=300)

    print("Number of finished trials: {}".format(len(study.trials)))

    print("Best trial:")
    trial = study.best_trial

    print("  Value: {}".format(trial.value))

    print("  Params: ")
    for key, value in trial.params.items():
        print("    {}: {}".format(key, value))


    return trial

def main():
    pl.seed_everything(666)
    trial = GridSearch() #CAMBIA NOME A STO QUA
    # I wonder if GridSearch does full training too...
     # Save trial as pickle
    with open('trial.pickle', 'wb') as f:
        pickle.dump(trial, f)
  

if __name__ == "__main__":
    main()
