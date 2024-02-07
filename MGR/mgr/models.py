import numpy as np

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
from torch.optim import Adam
import pytorch_lightning as pl

from mgr.utils_mgr import compute_metrics
#from sklearn.metrics import confusion_matrix, f1_score
from torchmetrics.classification import MulticlassConfusionMatrix, MulticlassF1Score
# Define a general LightningModule (nn.Module subclass)
# A LightningModule defines a full system (ie: a GAN, autoencoder, BERT or a simple Image Classifier).
class LitNet(pl.LightningModule):
    
    def __init__(self, model_net, lr=1, config=None):
       
        super().__init__()
        # super(NNET2, self).__init__() ? 
        
        print('Network initialized')
        
        self.net = model_net

        self.confusion_matrix = MulticlassConfusionMatrix(num_classes=8)
        self.f1_score = MulticlassF1Score(num_classes=8, average='macro')
        #self.val_loss = []
        #self.train_loss = []
        #self.best_val = np.inf
        """
        Credo abbia più senso salvare una CM, piuttosto che una lista di predictions e true label, per poi calcolare cm solo alla fine
        """
        # Initialize confusion matrix
        # The confusion matrix is a square matrix with dimensions equal to the number of classes
        # The confusion matrix is initialized as an empty array.
        # The confusion matrix is updated at each training step.
        # The confusion matrix is a sum of all the confusion matrices of the batches.
        # number of genres is computed as the number of output features of the last layer of the network [-1] and assuming that the
        # last layer is a Linear layer [-2] ([-1][-1] is the softmax layer)
        number_of_genres = list(self.net.children())[-1][-2].out_features
        """
        It is necessary to initialize the confusion matrix with the appropriate dimensions.
        Otherwise if the first batch has a label that is not present in the first batch, the confusion matrix will have the wrong dimensions.
        """
        #self.confusion_matrix =  np.empty((number_of_genres, number_of_genres))
        # Initialize f1 score as 0
        # f1 score is 1 when there are no false positives and false negatives
        # f1 score is 0 when there are no true positives and true negatives (all predictions are wrong)
       # self.f1_score = 0    

    # If no configurations regarding the optimizer are specified, use the default ones
        try:
            self.optimizer = Adam(self.net.parameters(),
                                       lr=config["lr"],rho=config["rho"], eps=config["eps"], weight_decay=config["weight_decay"])
        except:
                print("Using default optimizer parameters")
                self.optimizer = Adam(self.net.parameters(), lr = lr)


    def forward(self,x):
        return self.net(x)

    # Training_step defines the training loop. 
    def training_step(self, batch, batch_idx=None):
        # training_step defines the train loop. It is independent of forward
        x_batch     = batch[0]
        label_batch = batch[1]
        out         = self.net(x_batch)
        loss        = F.cross_entropy(out, label_batch) 

        
        #Estimation of model accuracy
        self.confusion_matrix.update(out.argmax(dim=1), label_batch.argmax(dim=1))
        self.f1_score.update(out.argmax(dim=1), label_batch.argmax(dim=1))
       
        return loss
    
    def on_train_epoch_end(self):
        print("On train epoch end dovresti salvare sta confusion matrix da qualche parte")

        print("computing confusion matrix")
        cm = self.confusion_matrix.compute()
        print(cm)
       

        print("computing f1 score")
        self.log("f1_score",self.f1_score.compute())
       # print(self.f1_score.c)
        
        print("resetting confusion matrix")
        self.confusion_matrix.reset()
        print("resetting f1 score")
        self.f1_score.reset()


        print(self.f1_score)

    def validation_step(self, batch, batch_idx=None):
        # validation_step defines the validation loop. It is independent of forward
        # When the validation_step() is called,
        # the model has been put in eval mode and PyTorch gradients have been disabled. 
        # At the end of validation, the model goes back to training mode and gradients are enabled.
        x_batch     = batch[0]
        label_batch = batch[1]

        out  = self.net(x_batch)
        loss = F.cross_entropy(out, label_batch)

        #Estimation of model accuracy
        """
        Validation accuracy is computed as follows.
        label_batch are the true labels. They are one-hot encoded (eg [1,0,0,0,0,0,0,0]). 
        out are the predicted labels. They are a 8-dim vector of probabilities.
        argmax checks what is the index with the highest probability. Each index is related to a Music Genre.
        If the indexes are equal the classification is correct.
        """
         #Evaluation of metrics
        # Accuracy is computed with explicit computation of True Positive and True Negative.
        # Should be equal to accuract computed as val_acc = np.sum(np.argmax(label_batch.detach().cpu().numpy(), axis=1) == np.argmax(out.detach().cpu().numpy(), axis=1)) / len(label_batch)
        """
        accuracy, precision, recall, specificity, f1 = compute_metrics(out, label_batch)

        val_acc  = accuracy.mean()
        val_prec = precision.mean()
        val_rec  = recall.mean()
        val_spec = specificity.mean()
        val_f1   = f1.mean()
        print("Validation accuracy: ", val_acc)
        print("Validation precision: ", val_prec)
        print("Validation recall: ", val_rec)
        print("Validation specificity: ", val_spec)
        print("Validation f1: ", val_f1)
        print("\n")

        self.log("val_loss", loss.item(), prog_bar=True)
        self.log("val_acc", val_acc, prog_bar=True)
        self.log("val_prec", val_prec, prog_bar=True)
        self.log("val_rec", val_rec, prog_bar=True)
        self.log("val_spec", val_spec, prog_bar=True)
        self.log("val_f1", val_f1, prog_bar=True)


        val_acc_usual = np.sum(np.argmax(label_batch.detach().cpu().numpy(), axis=1) == np.argmax(out.detach().cpu().numpy(), axis=1)) / len(label_batch)

        #self.val_loss.append(loss.item())
        #self.log("val_loss", loss.item(), prog_bar=True)
        self.log("val_acc_usual", val_acc_usual, prog_bar=True)
        """

    def test_step(self, batch, batch_idx):
        # this is the test loop
        x_batch = batch[0]
        label_batch = batch[1]
        out = self.net(x_batch)
        loss = F.cross_entropy(out, label_batch)
        
        """
        accuracy, precision, recall, specificity, f1 = compute_metrics(out, label_batch)

        test_acc  = accuracy.mean()
        test_prec = precision.mean()
        test_rec  = recall.mean()
        test_spec = specificity.mean()
        test_f1   = f1.mean()
        print("Test accuracy: ", test_acc)
        print("Test precision: ", test_prec)
        print("Test recall: ", test_rec)
        print("Test specificity: ", test_spec)
        print("Test f1: ", test_f1)
        print("\n")
       
        self.log("test_loss", loss.item(), prog_bar=True)
        self.log("test_acc", test_acc, prog_bar=True)
        self.log("test_prec", test_prec, prog_bar=True)
        self.log("test_rec", test_rec, prog_bar=True)
        self.log("test_spec", test_spec, prog_bar=True)
        self.log("test_f1", test_f1, prog_bar=True)
        
        test_acc_usual = np.sum(np.argmax(label_batch.detach().cpu().numpy(), axis=1) == np.argmax(out.detach().cpu().numpy(), axis=1)) / len(label_batch)

        #self.log("test_loss", loss.item(), prog_bar=True)
        self.log("test_acc", test_acc_usual, prog_bar=True)
        """
    def configure_optimizers(self):

        return self.optimizer



class NNET1D(nn.Module):
        
    def __init__(self):
        super(NNET1D, self).__init__()
        
        
        self.c1 = nn.Sequential(
            nn.Conv1d(in_channels=1, out_channels=16, kernel_size=128, stride=32, padding=64),
            nn.BatchNorm1d(16),
            nn.ReLU(inplace = True),
            nn.MaxPool1d(kernel_size=4, stride=4),
            nn.Dropout(p=0.2),
        )

        self.c2 = nn.Sequential(
            nn.Conv1d(in_channels=16, out_channels=32, kernel_size=32, stride=2, padding=16),
            nn.BatchNorm1d(32),
            nn.ReLU(inplace = True),
            nn.MaxPool1d(kernel_size=2, stride=2),
            nn.Dropout(p=0.2)
        )

        self.c3 = nn.Sequential(
            nn.Conv1d(in_channels=32, out_channels=64, kernel_size=16, stride=2, padding=8),
            nn.BatchNorm1d(64),
            nn.ReLU(inplace = True),
            nn.MaxPool1d(kernel_size=2, stride=2),
            nn.Dropout(p=0.2)
        )
        
        #Trying to add 4th convolutional block
        self.c4 = nn.Sequential(
            nn.Conv1d(in_channels=64, out_channels=128, kernel_size=8,stride=2, padding=4),
            nn.BatchNorm1d(128),
            nn.ReLU(inplace = True),
            nn.Dropout(p=0.2)
        )
        

        self.fc = nn.Sequential(
            nn.Linear(256, 128), 
            nn.ReLU(inplace = True),
            nn.Dropout(p=0.2),
            nn.Linear(128, 64),
            nn.ReLU(inplace = True),
            nn.Dropout(p=0.2),
            nn.Linear(64, 8),
            nn.Softmax(dim=1)
        )

    def forward(self, x):

        c1 = self.c1(x)
        
        c2 = self.c2(c1)
        
        c3 = self.c3(c2)
        
        c4 = self.c4(c3)


        max_pool = F.max_pool1d(c4, kernel_size=64)
        avg_pool = F.avg_pool1d(c4, kernel_size=64)

        #Concatenate max and average pooling
        x = torch.cat([max_pool, avg_pool], dim = 1) 

        
        # x dimensions are [batch_size, channels, length, width]
        # All dimensions are flattened except batch_size  
        x = torch.flatten(x, start_dim=1)

        x = self.fc(x)
        return x 


class NNET2D(nn.Module):
        
    def __init__(self,initialisation="xavier"):
        super(NNET2D, self).__init__()
        
        
        self.c1 = nn.Sequential(
            nn.Conv2d(in_channels=1, out_channels=256,kernel_size=(4,513)),
            nn.BatchNorm2d(256),
            nn.ReLU(),
            nn.Dropout2d(.2)
        )

        self.c2 = nn.Sequential(
            nn.Conv2d(in_channels=256, out_channels=256, kernel_size=(4, 1),padding=(2,0)),
            nn.BatchNorm2d(256),
            nn.ReLU(),
            nn.Dropout2d(.2)
        )

        self.c3 = nn.Sequential(
            nn.Conv2d(in_channels=256, out_channels=256, kernel_size=(4, 1),padding=(1,0)),
            nn.BatchNorm2d(256),
            nn.ReLU(),
            nn.Dropout2d(.2)
        )
                

        self.fc = nn.Sequential(
            nn.Linear(512, 300),
            nn.ReLU(),
            nn.Dropout(p=0.2),
            nn.Linear(300, 150),
            nn.ReLU(),
            nn.Dropout(p=0.2),
            nn.Linear(150, 8),
            nn.Softmax(dim=1)
        )

        # I remove the initialization part because it's not needed


    def forward(self,x):
        
        c1 = self.c1(x) 
        c2 = self.c2(c1)
        c3 = self.c3(c2)
        x = c1 + c3
        max_pool = F.max_pool2d(x, kernel_size=(125,1))
        avg_pool = F.avg_pool2d(x, kernel_size=(125,1))
        x = torch.cat([max_pool,avg_pool],dim=1)
        x = self.fc(x.view(x.size(0), -1)) # Reshape x to fit in linear layers. Equivalent to F.Flatten
        return x 

class MixNet(nn.Module):
    def __init__(self, conv_block1D, conv_block2D):
        super(MixNet, self).__init__()
        self.conv_block1D = conv_block1D
        self.conv_block2D = conv_block2D

        self.dropout = nn.Dropout(p=0.5)  # Add dropout layer

        self.classifier = nn.Sequential(
            nn.Linear(512+2048, 128),
            nn.ReLU(),
            self.dropout,   
            nn.Linear(128, 8),
            nn.Softmax(dim=1)
        )

        self.apply(self._init_weights)

    def _init_weights(self, module):
        # Initialize only self.classifer weights
        # We need the weights of the trained CNNs
        if isinstance(module, nn.Linear):
            nn.init.xavier_uniform_(module.weight)
            nn.init.constant_(module.bias, 0.0)
        
        

    def forward(self, x):
        audio = x[0]
        mel   = x[1]
        
        conv2d = self.conv_block2D(mel)
        max_pool = F.max_pool2d(conv2d, kernel_size=(125,1))
        avg_pool = F.avg_pool2d(conv2d, kernel_size=(125,1))
        cat2d = torch.cat([max_pool,avg_pool],dim=1)
        cat2d = cat2d.view(cat2d.size(0), -1) # cat2d shape torch.Size([1, 512])
        
        conv1d = self.conv_block1D(audio)
        max_pool = F.max_pool1d(conv1d, kernel_size=125)
        avg_pool = F.avg_pool1d(conv1d, kernel_size=125)
        cat1d = torch.cat([max_pool,avg_pool],dim=1)
        cat1d = cat1d.view(cat1d.size(0), -1) # cat1d dim = torch.Size([batch_size, 2048])

        # Concatanate the two outputs and pass it to the classifier
        # cat1d dim = torch.Size([batch_size, 2048])
        # cat2d dim = torch.Size([batch_size, 512])
        x = torch.cat([cat1d, cat2d], dim=1) 
        x = self.dropout(x)  # Add dropout layer
        x = self.classifier(x)
        return x



class Encoder(nn.Module):

    
    def __init__(self, encoded_space_dim):
        super().__init__()
        
        ### Convolutional section
        self.encoder_cnn = nn.Sequential(
            # First convolutional layer
            nn.Conv2d(in_channels=1, out_channels=8, kernel_size=3, 
                      stride=2, padding=1),
            nn.ReLU(True),
            nn.BatchNorm2d(8),
            nn.Dropout2d(0.2),
            # Second convolutional layer
            nn.Conv2d(in_channels=8, out_channels=16, kernel_size=3, 
                      stride=2, padding=1),
            nn.ReLU(True),
            nn.BatchNorm2d(16),
            nn.Dropout2d(0.2),
            # Third convolutional layer
            nn.Conv2d(in_channels=16, out_channels=32, kernel_size=3, 
                      stride=2, padding=0),
            nn.ReLU(True),
            nn.BatchNorm2d(32),
            nn.Dropout2d(0.2),
        )
        
        ### Flatten layer
        self.flatten = nn.Flatten(start_dim=1)

        ### Linear section
        self.encoder_lin = nn.Sequential(
            # First linear layer
            nn.Linear(in_features= 32, out_features=64),
            nn.ReLU(True),
            # Second linear layer
            nn.Linear(in_features=64, out_features=encoded_space_dim),
            nn.ReLU(True),
        )
        

        self._initialize_weights()

    def _initialize_weights(self):
        for module in self.modules():
            if isinstance(module, nn.Conv2d) or isinstance(module, nn.ConvTranspose2d):
                init.xavier_uniform_(module.weight)
                if module.bias is not None:
                    init.constant_(module.bias, 1)
            elif isinstance(module, nn.Linear):
                init.xavier_uniform_(module.weight)
                if module.bias is not None:
                    init.constant_(module.bias, 1)
    def forward(self, x):
        # Apply convolutions
        x = self.encoder_cnn(x)
        #print("encoder shape",x.shape)
        """
        This avg pool may be too aggressive.
        """
        x = F.avg_pool2d(x, kernel_size=x.size()[2:])
        #print("maxpool shape",x.shape)
        # Flatten
        x = self.flatten(x)
        #print("flatten shape",x.shape)
        # # Apply linear layers
        x = self.encoder_lin(x)
        return x
    

class Decoder(nn.Module):
    
    def __init__(self, encoded_space_dim):
        super().__init__()

        ### Linear section
        self.decoder_lin = nn.Sequential(
            # First linear layer
            nn.Linear(in_features=encoded_space_dim, out_features=64),
            nn.ReLU(True),
            # Second linear layer
            nn.Linear(in_features=64, out_features= 32),
            nn.ReLU(True),
        )

        ### Unflatten
        self.unflatten = nn.Unflatten(dim=1, unflattened_size=(32, 1, 1))

        ### Convolutional section
        self.decoder_conv = nn.Sequential(
            # First transposed convolution
            nn.ConvTranspose2d(in_channels=32, out_channels=16, kernel_size=3, 
                               stride=2, output_padding=(1,0)),
            nn.ReLU(True),
            nn.BatchNorm2d(16),
            nn.Dropout2d(0.2),
           
            # Second transposed convolution
            nn.ConvTranspose2d(in_channels=16, out_channels=8, kernel_size=3, 
                               stride=2, padding=1, output_padding=(1,0)),
            nn.ReLU(True),
            nn.BatchNorm2d(8),
            nn.Dropout2d(0.2),
           
            # Third transposed convolution
            nn.ConvTranspose2d(in_channels=8, out_channels=1, kernel_size=3, 
                               stride=2, padding=1, output_padding=(1,0)),
            nn.ReLU(True),
            nn.BatchNorm2d(1),
            nn.Dropout2d(0.2),
           
        )
        self._initialize_weights()

    def _initialize_weights(self):
        for module in self.modules():
            if isinstance(module, nn.Conv2d) or isinstance(module, nn.ConvTranspose2d):
                init.xavier_uniform_(module.weight)
                if module.bias is not None:
                    init.constant_(module.bias, 1)
            elif isinstance(module, nn.Linear):
                init.xavier_uniform_(module.weight)
                if module.bias is not None:
                    init.constant_(module.bias, 1)
    

    def forward(self, x):
        #print("input of decoder",x.shape)
        # Apply linear layers
        x = self.decoder_lin(x)
        #print("decoder linear out",x.shape)
        # Unflatten
        x = self.unflatten(x)
        #print("unflattened shape",x.shape)
        
        # Apply upsampling
        x = F.interpolate(x, size=(15,64), mode='nearest')
        #print("interpolate out shape",x.shape)
        # Apply transposed convolutions
        x = self.decoder_conv(x)
        #print("decoder conv out",x.shape)   
        # Apply a sigmoid to force the output to be between 0 and 1 (valid pixel values)
        x = torch.sigmoid(x)
        return x
    
class Autoencoder(nn.Module):
        
        def __init__(self, encoded_space_dim=64):
            super().__init__()
            self.encoder = Encoder(encoded_space_dim)
            self.decoder = Decoder(encoded_space_dim)
            
            self._initialize_weights()

        def _initialize_weights(self):
            for module in self.modules():
                if isinstance(module, nn.Conv2d) or isinstance(module, nn.ConvTranspose2d):
                    init.xavier_uniform_(module.weight)
                    if module.bias is not None:
                        init.constant_(module.bias, 1)
                elif isinstance(module, nn.Linear):
                    init.xavier_uniform_(module.weight)
                    if module.bias is not None:
                        init.constant_(module.bias, 1)
                
        def forward(self, x):
            #print("very input shape",x.shape)
            x = self.encoder(x)
            x = self.decoder(x)
            return x
