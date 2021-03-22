import numpy as np
import multiprocessing as mp
import torch
import librosa
import random
import warnings
import jams
import glob
from torch.utils.data import DataLoader, Dataset

class CQTsDataset(Dataset):
    """CQTs dataset."""

    def __init__(self, root_dir, n_triplets, delta=(16, 16, 96), dim_cqt=(72,128*4)):
        """
        Args:
            root_dir (string): Directory with all the cqts.
        """
        self.root_dir = root_dir
        self.n_files = len(glob.glob(root_dir + "audio/*.mp3")) 
        self.delta = delta
        self.n_triplets = n_triplets
        self.dim_cqt = dim_cqt

    def __len__(self):
        return self.n_files

    def __getitem__(self, idx):
        if torch.is_tensor(idx):
            idx = idx.tolist()
        cqts = np.load(self.root_dir + "cqts/cqts" + str(idx) + ".npy")
        dp, dnmin, dnmax = self.delta
        L = np.shape(cqts)[0]
        
        cqts_batch = torch.empty(self.n_triplets, 3, self.dim_cqt[0], self.dim_cqt[1])
        for j in range(self.n_triplets):
            a = np.random.randint(2, L-2);
            p = np.random.randint(max(a - dp, 2), min(a + dp, L-2))
            n1 = np.random.randint(max(a - dnmax, 2), max(a - dnmin, 3))
            n2 = np.random.randint(min(a + dnmin, L-3), min(a + dnmax, L-2))
            n = int(random.choice([n1,n2]))
            
            
            cqts_a = np.append(cqts[a - 2], cqts[a - 1], axis=1)
            cqts_a = np.append(cqts_a, cqts[a], axis=1)
            cqts_a = np.append(cqts_a, cqts[a +1], axis=1)
            
            cqts_p = np.append(cqts[p - 2], cqts[p - 1], axis=1)
            cqts_p = np.append(cqts_p, cqts[p], axis=1)
            cqts_p = np.append(cqts_p, cqts[p +1], axis=1)
            
            cqts_n = np.append(cqts[n - 2], cqts[n - 1], axis=1)
            cqts_n = np.append(cqts_n, cqts[n], axis=1)
            cqts_n = np.append(cqts_n, cqts[n +1], axis=1)
            
            cqts_batch[j, 0] = torch.from_numpy(cqts_a)
            cqts_batch[j, 1] = torch.from_numpy(cqts_p)
            cqts_batch[j, 2] = torch.from_numpy(cqts_n)

        return cqts_batch
    


def compute_dataset(i, n_bins=72, n_octave=6, min_freq=40, n_t = 128):
    bpo = int(n_bins/n_octave)
    # Compute beat-centered CQTs for each track
    #for i, tp in enumerate(paths):
    print("track n°" + str(i + 1) + "/" + str(len(paths)))
    y, sr = librosa.load(paths[i])
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr, trim=False, units='samples')
    L = len(beats)

    cqts = np.empty((L, n_bins, n_t))
    for j in range(0, L-1):
        n_samples = beats[j+1] - beats[j]
        hop_size = int(np.ceil(n_samples/(n_t*32))*32) # hop_size must be multiple of 2^5 for 6 octaves CQT
        cqts_j = librosa.cqt(y[beats[j]:int(beats[j]+hop_size*(n_t-1))], sr, hop_size, fmin=min_freq, n_bins=n_bins, bins_per_octave=bpo)
        cqts[j] = cqts_j


    np.save("./cqts/" + "cqts" + str(i), cqts)

    
if __name__ == "__main__":
    root_path = "/ldaphome/atiam-1005/music-structure-estimation/data/Isophonics/"
    warnings.filterwarnings("ignore")
    paths = glob.glob(root_path+"audio/*.mp3")
    a_pool = mp.Pool()
    a_pool.map(compute_dataset, range(len(paths)))
    warnings.filterwarnings("always")