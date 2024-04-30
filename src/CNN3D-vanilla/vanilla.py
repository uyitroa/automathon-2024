import pytorch_lightning as pl
import torch.nn as nn
import torch
import argparse
import yaml
import munch
from pytorch_lightning.callbacks import ModelCheckpoint
import wandb
import torchinfo


class CNN3d(nn.Module):
    def __init__(self, channel_list):
        super().__init__()

        self.conv1 = nn.Conv3d(channel_list[0], channel_list[1], kernel_size=3, padding=1)
        self.conv2 = nn.Conv3d(channel_list[1], channel_list[2], kernel_size=3, padding=1)
        self.conv3 = nn.Conv3d(channel_list[2], channel_list[3], kernel_size=3, padding=1)
        self.conv4 = nn.Conv3d(channel_list[3], channel_list[4], kernel_size=3, padding=1)
        self.pool = nn.MaxPool3d(2)
        self.relu = nn.ReLU()

    def forward(self, x):
        x = self.relu(self.conv1(x))
        x = self.pool(x)
        x = self.relu(self.conv2(x))
        x = self.pool(x)
        x = self.relu(self.conv3(x))
        x = self.pool(x)
        x = self.relu(self.conv4(x))
        x = self.pool(x)
        return x


class PredictionHead(nn.Module):
    def __init__(self, in_features):
        super(PredictionHead, self).__init__()
        self.linear1 = nn.Linear(in_features, 1)
        self.flatten = nn.Flatten()

    def forward(self, x):
        x = self.linear1(self.flatten(x))
        return torch.sigmoid(x)


class Baseline(pl.LightningModule):
    def __init__(self, config):
        super(Baseline, self).__init__()
        self.config = config
        self.model = CNN3d(config.channels)
        self.head = PredictionHead(config.channels[-1] * 4 * 4 * 4)
        self.loss = nn.BCELoss()

    def forward(self, x):
        return self.model(x)

    def training_step(self, batch, batch_idx):
        x, y = batch
        y_hat = self.model(x)
        loss = self.loss(y_hat, y)
        # wandb.log({"train loss": loss})
        return loss

    def configure_optimizers(self):
        return torch.optim.Adam(self.parameters(), lr=self.config.lr)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config_path', type=str, default="../../configs/CNN3D-vanilla/config.yaml")

    args = parser.parse_args()
    with open(args.config_path, 'r') as f:
        yamlfile = munch.munchify(yaml.safe_load(f))
    config = yamlfile.config


    model = CNN3d(config.channels)
    torchinfo.summary(model, (1, 3, 64, 64, 64))


    # wandb.init(project="Deepfake challenge", config=config, group=yamlfile.name, entity="automathon")
    #
    # model = Baseline(config)
    #
    # checkpoint_callback = ModelCheckpoint(dirpath="../../checkpoints/baseline/", every_n_train_steps=2, save_top_k=1, save_last=True,
    #                              monitor="val loss", mode="min")
    # checkpoint_callback.CHECKPOINT_NAME_LAST = yamlfile.name
    #
    # trainer = pl.Trainer(max_epochs=config.epoch,
    #                      accelerator="auto",
    #                      precision='16-mixed',
    #                      callbacks=[checkpoint_callback],)
    #
    # train_loader = torch.utils.data.DataLoader(train_dataset, batch_size=config.batch_size, shuffle=True)
    # val_loader = torch.utils.data.DataLoader(val_dataset, batch_size=config.batch_size)
    #
    # trainer.fit(model, train_loader, val_loader)


