import numpy as np
import scipy
import matplotlib.pyplot as plt
from CoverAlgorithm import *

from joblib import Parallel, delayed

import librosa
import scipy

from librosa import util
from librosa import filters


class Simple(CoverAlgorithm):
    """
    Attributes
    ----------
    Same as CoverAlgorithms, plus
    SSLEN=10, the length of subsequence used by SiMPle
    WIN=200, the window length for the dimensionality reduction
    SKIP=100, how many frames the dim reduction will skip each step
    """
    def __init__(self, datapath="crema_benchmark", SSLEN=10, WIN=200, SKIP=100):
        CoverAlgorithm.__init__(self, "Simple - CREMA", datapath)
        self.SSLEN = SSLEN
        self.WIN = WIN
        self.SKIP = SKIP

    def load_features(self, i, do_plot=False):
        
        feats = CoverAlgorithm.load_features(self, i)
        crema_orig = feats['crema'].T
        
        new_crema = np.zeros((crema_orig.shape[0],(int)(crema_orig.shape[1]/self.SKIP)))

        for i in range(0,new_crema.shape[1]):
            new_crema[:,i] = np.mean(crema_orig[:,i*self.SKIP:i*self.SKIP+self.WIN],axis=1)

        return self.smooth(new_crema)
        
    def oti(self, seq_a, seq_b):
        
        profile_a = np.sum(seq_a,1);
        profile_b = np.sum(seq_b,1);

        oti_vec = np.zeros(12)
        for i in range(12):
            oti_vec[i] = np.dot(profile_a,np.roll(profile_b,i,axis=0))

        sorted_index = np.argsort(oti_vec)
        
        return np.roll(seq_b, sorted_index[-1], axis=0), sorted_index

    def smooth(self, feat, win_len_smooth = 4):    

        '''
        This code is similar to the one used on librosa for smoothing cens: 
        https://librosa.github.io/librosa/generated/librosa.feature.chroma_cens.html
        '''
        win = filters.get_window('hann', win_len_smooth + 2, fftbins=False)
        win /= np.sum(win)
        win = np.atleast_2d(win)

        feat = scipy.signal.convolve2d(feat, win, mode='same', boundary='fill')
        return util.normalize(feat, norm=2, axis=0)
    
    def simple_sim(self, seq_a, seq_b):
    
        # prerequisites
        ndim = seq_b.shape[0]   
        seq_a_len = seq_a.shape[1]
        seq_b_len = seq_b.shape[1]
        
        matrix_profile_len = seq_a_len - self.SSLEN + 1;
        
        # the "inverted" dot products will be used as the first value for reusing the dot products
        prods_inv = np.full([ndim,seq_a_len+self.SSLEN-1], np.inf)
        first_subseq = np.flip(seq_b[:,0:self.SSLEN],1)
            
        for i_dim in range(0,ndim):
            prods_inv[i_dim,:] = np.convolve(first_subseq[i_dim,:],seq_a[i_dim,:])
        prods_inv = prods_inv[:, self.SSLEN-1:seq_a_len]
           
        # windowed cumulative sum of the sequence b
        seq_b_cum_sum2 = np.insert(np.sum(np.cumsum(np.square(seq_b),1),0), 0, 0)
        seq_b_cum_sum2 = seq_b_cum_sum2[self.SSLEN:]-seq_b_cum_sum2[0:seq_b_len - self.SSLEN + 1]
        
        subseq_cum_sum2 = np.sum(np.square(seq_a[:,0:self.SSLEN]))
        
        # first distance profile
        first_subseq = np.flip(seq_a[:,0:self.SSLEN],1)
        dist_profile = seq_b_cum_sum2 + subseq_cum_sum2
        
        prods = np.full([ndim,seq_b_len+self.SSLEN-1], np.inf)
        for i_dim in range(0,ndim):
            prods[i_dim,:] = np.convolve(first_subseq[i_dim,:],seq_b[i_dim,:])
            dist_profile -= (2 * prods[i_dim,self.SSLEN-1:seq_b_len])
        prods = prods[:, self.SSLEN-1:seq_b_len] # only the interesting products
            
        matrix_profile = np.full(matrix_profile_len, np.inf)
        matrix_profile[0] = np.min(dist_profile)

        # for all the other values of the profile
        for i_subseq in range(1,matrix_profile_len):
            
            sub_value = seq_a[:,i_subseq-1, np.newaxis] * seq_b[:,0:prods.shape[1]-1]
            add_value = seq_a[:,i_subseq+self.SSLEN-1, np.newaxis] * seq_b[:, self.SSLEN:self.SSLEN+prods.shape[1]-1]
            
            prods[:,1:] = prods[:,0:prods.shape[1]-1] - sub_value + add_value
            prods[:,0] = prods_inv[:,i_subseq]
            
            subseq_cum_sum2 += -np.sum(np.square(seq_a[:,i_subseq-1])) + np.sum(np.square(seq_a[:,i_subseq+self.SSLEN-1]))
            dist_profile = seq_b_cum_sum2 + subseq_cum_sum2 - 2 * np.sum(prods,0)
            
            matrix_profile[i_subseq] = np.min(dist_profile)
        
        return np.median(matrix_profile)
    
    
    def similarity(self, i, j):
        
        seq_a = self.load_features(i)
        seq_b, _ = self.oti(seq_a, self.load_features(j))               
        
        self.D[i, j] = 1/self.simple_sim(seq_a, seq_b)
        self.D[j, i] = 1/self.simple_sim(seq_b, seq_a)
            
        return i, j, self.D[i, j], self.D[j, i]


def simple_allpairwise():
    """
    Show how one might do all pairwise comparisons between songs,
    with code that is amenable to parallelizations.
    """
    from itertools import combinations
    import scipy.io as sio
    simple = Simple()
    for idx, (i, j) in enumerate(combinations(range(len(simple.filepaths)), 2)):
        simple.similarity(i, j)
        if idx%100 == 0:
            print((i, j))
    
    # In the serial case, I'm saving all pairwise comparisons to disk
    # but in the parallel case, there should probably be a separate
    # file for each pair
    sio.savemat("SimpleCREMA.mat", {"D":simple.D})
    simple.getEvalStatistics()


if __name__ == '__main__':
    simple_allpairwise()
