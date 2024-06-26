import argparse
import torch
import torch.nn as nn
from double import Baseline
import yaml
import munch
import json
import pandas as pd
import os


if __name__ == '__main__':
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    parser = argparse.ArgumentParser()
    parser.add_argument('--config_path', type=str, default="../../configs/CNNErwin/config.yaml")
    parser.add_argument('--checkpoint_path', type=str)
    parser.add_argument('--method', type=str, default="none")
    args = parser.parse_args()

    with open(args.config_path, 'r') as f:
        yamlfile = munch.munchify(yaml.safe_load(f))
    config = yamlfile.config

    model = Baseline.load_from_checkpoint(args.checkpoint_path, config=config)
    model.eval()
    model.to(device)

    sample_submission = pd.read_csv("/raid/home/automathon_2024/account24/data/sample_submission.csv") # id, ...
    datasetcsv = pd.read_csv("/raid/home/automathon_2024/account24/data/dataset.csv")  # id, file

    id_to_file = {row['id']: row['file'] for _, row in datasetcsv.iterrows()}

    for i, row in sample_submission.iterrows():
        video_id = row['id']
        file = id_to_file[video_id]
        file = file[:-4] + ".pt"
        video_path = f"/raid/home/automathon_2024/account24/data/processed3/{file}"

        if not os.path.exists(video_path):
            # sample_submission.loc[i, 'label'] = 1
            continue

        faces = torch.load(video_path)
        for start_middle in range(0, faces.size(1) - config.n_frames):
            faces = faces[:, start_middle:start_middle+config.n_frames]

            x = faces.float()

            x_prime1 = torch.mean(x[:, 1:4, :, :] - x[:, 0:3, :, :], dim=0)
            x_prime2 = torch.mean(x[:, 2:5, :, :] - x[:, 1:4, :, :], dim=0)
            x_prime3 = torch.mean(x[:, 3:6, :, :] - x[:, 2:5, :, :], dim=0)

            xprime = torch.stack([x_prime1, x_prime2, x_prime3], dim=0)

            faces = faces.unsqueeze(0).half().to(device) / 255.0
            xprime = xprime.unsqueeze(0).half().to(device) / 255.0

            with torch.cuda.amp.autocast():
                with torch.no_grad():
                    if(args.method == 'mean'):
                        print("Mean inference")
                        y_hat = model(faces.permute(2,1,0,3,4)).mean()
                    else:
                        print('Default inference')
                        y_hat = model(faces, xprime)

        sample_submission.loc[i, 'label'] = y_hat.item()
        print(f"{i}, {video_id}, {y_hat.item()}")

    sample_submission.to_csv("submission.csv", index=False)