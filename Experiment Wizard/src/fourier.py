##--------------------------------------%%
##    Perform Fast Fourier Transform    ##
##          on Emotiv EEG data          ##
##         Author: Jeroen Kools         ##
##        Last changed Jan 16 2011      ##
##--------------------------------------##

from numpy import fft, arange, r_

def doFFT(input, description):

    i = 0
    signal = arange(len(input))
    for line in input:
        signal[i] = float(line)
        i += 1

    sample_rate = 128.0                     
    duration = len(signal)/sample_rate

    alpha = 0
    beta = 0
    delta = 0
    theta = 0

    if len(signal) > 0:
        time = r_[0:duration:(1/sample_rate)].astype(float)
        N = len(time)
        S = fft.fft(signal)
        freq = fft.fftfreq(N, d=1/sample_rate)
        avg = sum(signal)/len(signal)
        
        # sum total activity per waveband
    
        for n in range(N):   
            if (freq[n] >= 8) and (freq[n] <= 12):      # alpha
                alpha += abs(S[n])/(4*N)
            elif (freq[n] >= 12) and (freq[n] <= 30):   # beta
                beta += abs(S[n])/(18*N)
            elif (freq[n] >= 2) and (freq[n] <= 4):     # delta
                delta += abs(S[n])/(2*N)
            elif (freq[n] >= 4) and (freq[n] <= 7):    # theta
                theta += abs(S[n])/(3*N)

    return {'avg':avg, 'alpha':alpha, 'beta':beta, 'delta':delta, 'theta':theta}


