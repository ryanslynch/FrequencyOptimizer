import numpy as np
import scipy.linalg as linalg
import scipy.interpolate as interpolate
import scipy.optimize as optimize
from matplotlib.pyplot import *
from matplotlib import cm,rc
from matplotlib.ticker import FuncFormatter, MultipleLocator
import matplotlib.patches as patches
import DISS
import glob


rc('text',usetex=True)
rc('font',**{'family':'serif','serif':['Times New Roman'],'size':14})#,'weight':'bold'})
rc('xtick',**{'labelsize':16})
rc('ytick',**{'labelsize':16})
rc('axes',**{'labelsize':18,'titlesize':18})


def nolog(x,pos):
    return "$\hfill %0.1f$" % (10**x)
noformatter = FuncFormatter(nolog)
def nolog2(x,pos):
    return "$\hfill %0.2f$" % (10**x)
noformatter2 = FuncFormatter(nolog2)

def log(x,pos):
    y = x#np.log10(x)
    #print x,10**x
    #if y == 2:
    #    return "$\hfill 100$" #added
    if y == 1:
        return "$\hfill 10$"
    elif y == 0:
        return "$\hfill 1$"
    elif y == -1:
        return "$\hfill 0.1$"
    elif y == -2:
        return "$\hfill 0.01$"
    return "$\hfill 10^{%i}$" % x#np.log10(x) 

formatter = FuncFormatter(log)



def log100(x,pos):
    y = x#np.log10(x)
    #print x,10**x
    if y == 2:
        return "$\hfill 100$" #added
    elif y == 1:
        return "$\hfill 10$"
    elif y == 0:
        return "$\hfill 1$"
    elif y == -1:
        return "$\hfill 0.1$"
    elif y == -2:
        return "$\hfill 0.01$"
    return "$\hfill 10^{%i}$" % x#np.log10(x) 

formatter100 = FuncFormatter(log100)

# Copied from utilities.py
def uimshow(x,ax=None,origin='lower',interpolation='nearest',aspect='auto',**kwargs):
    if ax is not None:
        im=ax.imshow(x,origin=origin,interpolation=interpolation,aspect=aspect,**kwargs)
    else:
        im=imshow(x,origin=origin,interpolation=interpolation,aspect=aspect,**kwargs) # plt.
    return im









#K = 4.149 #ms GHz^2 pc^-1 cm^3
K = 4.149e3 #us GHz^2 pc^-1 cm^3  
# Note on units used: TOA errors in microseconds, observing frequencies in GHz, DM in pc cm^-3

LEVELS = np.array([np.log10(0.125),np.log10(0.25),np.log10(0.5),np.log10(1.0)])
LEVELS = np.array([np.log10(0.25),np.log10(0.5),np.log10(1.0),np.log10(2.0),np.log10(5.0)])
LEVELS = np.array([np.log10(0.25),np.log10(0.5),np.log10(1.0),np.log10(2.0),np.log10(5.0)])
LEVELS = np.array([np.log10(0.5),np.log10(1.0),np.log10(2.0),np.log10(5.0),np.log10(10.0)])
LEVELS = np.array([np.log10(0.5),np.log10(1.0),np.log10(2.0),np.log10(5.0),np.log10(10.0),np.log10(20.0)])

COLORS = ['k','0.25','0.5','0.75']
COLORS = ['k','0.25','0.5','0.75','1.0']
COLORS = ['k','0.2','0.4','0.6','0.8','1.0']

LWS = [2.5,2,1.5,1,0.5]
LWS = [2.5,2.25,2.0,1.75,1.5,1.25]

def epoch_averaged_error(C,var=False):
    # Stripped down version from rednoisemodel.py from the excess noise project
    N = len(C)
    UT = np.matrix(np.ones(N))
    U = UT.T
    CI = C.I
    C_E = np.dot(np.dot(UT,CI),U).I
    if var:
        return C_E[0,0]
    return np.sqrt(C_E[0,0])

def isMatrix(value):
    if type(value) == np.matrixlib.defmatrix.matrix or type(value) == np.ndarray:
        return True
    return False







def evalNonSimError(dtiss,nu1,nu2,tau):
    # dtiss at 1 GHz, tau in days
    # Returns error in microseconds
    # Equation 14
    return 6.5e-3 * abs(1.0/(nu1**2 - nu2**2)) * (tau / (dtiss/1000))**(5.0/6)

# DMnu-related variables
def F_beta(r,beta=11.0/3):
    return np.sqrt(2**((4-beta)/2.0) * (1 + r**((2*beta)/(beta-2)))**((beta-2)/2.0) - r**beta - 1)
def E_beta(r,beta=11.0/3):
    r2 = r**2
    return np.abs(r2 / (r2-1)) * F_beta(r,beta)
def evalDMnuError(dnuiss,nu1,nu2,g=0.46,q=1.15,screen=False,fresnel=False):
    # nu2 should be less than nu1
    # nu in GHz, dnuiss in GHz
    # return value in microseconds
    # Based on equation 25
    # if fresnel==True, the first argument is phiF
    if screen:
        g = 1
    if fresnel:
        phiF = dnuiss
    else:
        phiF = 9.6 * ((nu1 / dnuiss)/100)**(5.0/12) #equation 15
    r = nu1/nu2
    return 0.184 * g * q * E_beta(r) * (phiF**2 / (nu1 * 1000))





class PulsarNoise:
    def __init__(self,name,alpha=1.7,beta=2.75,dtd=None,dnud=None,taud=None,C1=1.16,A_e=27600.0,I_0=18.0,DM=0.0,D=1.0,T_e=100,tauvar=None,Weffs=None,W50s=None,sigma_Js=None,fillingfactor=0.2):
        self.name = name

        self.dtd = dtd

        if taud is not None:
            self.taud = taud
            self.dnud = C1 / (2*np.pi*taud)
        elif dnud is not None:
            self.dnud = dnud
            self.taud = C1 / (2*np.pi*dnud)

        self.C1 = C1
        self.A_e = A_e
        self.I_0 = I_0
        self.DM = DM
        self.D = D
        self.fillingfactor = fillingfactor
        self.T_e = T_e

        self.alpha = alpha
        self.beta = beta

        if tauvar is None:
            tauvar = self.taud / 2.0
        self.tauvar = tauvar

        self.Weffs = Weffs
        self.W50s = W50s
        self.sigma_Js = sigma_Js


class TelescopeNoise:
    def __init__(self,gain,epsilon=0.08,pi_V=0.1,eta=0.0,pi_L=0.0):
        pass





class FrequencyOptimizer:
    def __init__(self,psrnoise,numin=0.3,numax=10.0,dnu=0.05,nchan=100,log=False,nsteps=8,frac_bw=False,verbose=True,full_bandwidth=False,masks=None):

        self.psrnoise = psrnoise
        self.log = log
        self.frac_bw = frac_bw
        
        self.numin = numin
        self.numax = numax
        self.masks = masks
        if type(masks) == tuple: #implies it is not None
            self.masks = [masks]



        if self.frac_bw == False:
            if self.log == False:
                self.dnu = dnu
                self.Cs = np.arange(numin,numax,dnu)
                self.Bs = np.arange(numin,numax/2,dnu)
            else:
                MIN = np.log10(numin)
                MAX = np.log10(numax)
                self.Cs = np.logspace(MIN,MAX,(MAX-MIN)*nsteps+1)
                if full_bandwidth:
                    self.Bs = np.logspace(MIN,2*MAX,(2*MAX-MIN)*nsteps+1)
                else:
                    self.Bs = np.logspace(MIN,MAX,(MAX-MIN)*nsteps+1)
        else:
            if self.log == False:
                pass
            else:
                MIN = np.log10(numin)
                MAX = np.log10(numax)
                self.Cs = np.logspace(MIN,MAX,(MAX-MIN)*nsteps+1)
                self.Bs = np.logspace(MIN,MAX,(MAX-MIN)*nsteps+1)
                #self.Rs = np.logspace(np.log10(self.Bs[-1]/self.Cs[0]),np.log10(1.0),len(self.Cs))[::-1]
                self.Fs = np.logspace(np.log10(self.Bs[-1]/self.Cs[0]),np.log10(1.0),len(self.Cs))[::-1]
                #self.Fs = np.logspace(np.log10(self.Bs[0]/self.Cs[-1]),np.log10(2.0),len(self.Cs))
                self.Fs = np.logspace(np.log10(self.Bs[0]/self.Cs[-1]),np.log10(2.0),len(self.Cs))
                #print self.Fs
                #raise SystemExit



        self.nchan = nchan

        self.scattering_mod_f = None
        self.verbose = verbose


    def template_fitting_error(self,S,Weff=100.0,Nphi=2048): #Weff in microseconds
        Nphi = 1 #TEST; NOW PROBABLY A FIX
        return Weff / (S * np.sqrt(Nphi))



    def get_bandwidths(self,nus):
        if self.log == False:
            # assume equal bins?
            B = np.diff(nus)[0]
            #B = np.concatenate((np.diff(nus),self.dnu))
        else:
            logdiff = np.diff(np.log10(nus))[0]
            edges = 10**(np.concatenate(([np.log10(nus[0])-logdiff/2.0],np.log10(nus)+logdiff/2.0)))
            B = np.diff(edges)
        return B


    def build_template_fitting_cov_matrix(self,nus,T=1800.0,nuref=1.0,Tconst=20.0):
        '''
        
        '''
        
        Weffs = self.psrnoise.Weffs
        if type(Weffs) != np.ndarray:
            Weffs = np.zeros_like(nus)+Weffs
        B = self.get_bandwidths(nus)
       

        Tsys = Tconst + 20 * np.power(nus/0.408,-1*self.psrnoise.beta)

        tau = 0.0
        if self.psrnoise.DM != 0.0 and self.psrnoise.D != 0.0 and self.psrnoise.T_e != 0.0 and self.psrnoise.fillingfactor != 0:
            tau = 3.27e-8 * (self.psrnoise.fillingfactor/0.2)**-1 * self.psrnoise.DM**2 * self.psrnoise.D**-1 * np.power(self.psrnoise.T_e/100,-1.35)

        numer =  (self.psrnoise.I_0 * 1e-3) * np.power(nus/nuref,-1*self.psrnoise.alpha)*np.sqrt(B*1e9*T) * np.exp(-1*tau*np.power(nus/nuref,-2.1)) 

        denom = (2760.0 / self.psrnoise.A_e) * Tsys
        S = numer/denom
        sigmas = self.template_fitting_error(S,Weffs,1)

        if self.psrnoise.taud > 0.0:
            tauds = DISS.scale_tau_d(self.psrnoise.taud,nuref,nus)
            retval = self.scattering_modifications(tauds,Weffs)
            #retval = 1
            sigmas *= retval #??

        # Any enormous values should not cause an overflow
        inds = np.where(sigmas>1e100)[0]
        sigmas[inds] = 1e100


        # implement masks here
        if self.masks is not None:
            for i,mask in enumerate(self.masks):
                maskmin,maskmax = mask
                inds = np.where(np.logical_and(nus>=maskmin,nus<=maskmax))[0]
                sigmas[inds] = 0.0 #???
            

        return np.matrix(np.diag(sigmas**2))
        
    def build_jitter_cov_matrix(self):
        sigma_Js = self.psrnoise.sigma_Js
        if type(sigma_Js) != np.ndarray:
            sigma_Js = np.zeros(self.nchan)+sigma_Js

        retval = np.matrix(np.zeros((len(sigma_Js),len(sigma_Js))))
        if sigma_Js is not None:
            for i in range(len(sigma_Js)):
                for j in range(len(sigma_Js)):
                    retval[i,j] = sigma_Js[i] * sigma_Js[j]
        return retval

        
    def scattering_modifications(self,tauds,Weffs,filename="ampratios.npz",directory=None):
        if len(glob.glob(filename))!=1:
            if directory is None:
                directory = __file__.split("/")[0] + "/"
        else:
            directory = ""
        if type(Weffs) != np.ndarray:
            Weffs = np.zeros_like(nus)+Weffs

        if self.scattering_mod_f is None:
            data = np.load(directory+"ampratios.npz")
            ratios = data['ratios']
            ampratios = data['ampratios']
            Weffratios = data['Weffratios']
            errratios = data['errratios']
            
            logratios = np.log10(ratios)
            logerrratios = np.log10(errratios)

            self.scattering_mod_f = interpolate.interp1d(logratios,logerrratios)

        dataratios = np.array(tauds)/np.array(Weffs) #sigma_Ws?
        #print dataratios
        retval = np.zeros_like(dataratios) + 1.0
        inds = np.where(dataratios > 0.01)[0] #must be greater than this value
        retval[inds] = 10**self.scattering_mod_f(np.log10(dataratios[inds]))
        return retval
        
        
    def scintillation_noise(self,nus,dtd0,dnud0=None,taud0=None,nuref=1.0,C1=1.16,T=1800.0,etat=0.2,etanu=0.2):
        '''
        dtd0 in seconds
        dnud0 in GHz
        Uses an internal nsteps
        '''
        if taud0 is None:
            taud0 = 1e-3 * C1/(2*np.pi*dnud0) #taud0 in ns -> us
        elif dnud0 is None:
            dnud0 = 1e-3 * C1/(2*np.pi*taud0) #taud0 given in us, dnud0 in GHz
        numin = nus[0]
        numax = nus[-1]

        B = self.get_bandwidths(nus)
        dtd = DISS.scale_dt_d(dtd0,nuref,nus)
        dnud = DISS.scale_dnu_d(dnud0,nuref,nus)
        taud = DISS.scale_tau_d(taud0,nuref,nus)

        niss = (1 + etanu* B/dnud) * (1 + etat* T/dtd) 

        # check if niss >> 1?
        sigmas = taud/np.sqrt(niss)

        return np.matrix(np.diag(sigmas**2)) #these will be independent IF niss is large
        
        





    # Using notation from signal processing notes, lecture 17
    def DM_misestimation(self,nus,errs,covmat=False):
        N = len(nus)
        X = np.matrix(np.ones((N,2))) #design matrix
        for i,nu in enumerate(nus):
            X[i,1] = K/nu**2

        # Template-Fitting Errors
        if covmat is False:
            V = np.matrix(np.diag(errs**2)) #weights matrix
        else:
            V = errs
        XT = X.T
        VI = V.I
        P = np.dot(np.dot(XT,VI),X).I 




        # for now, ignore covariances and simply return the t_inf error    
        #print P

        template_fitting_var = P[0,0] #DM units for P[1,1] are incorrect?

        # Frequency-Dependent DM
        DM_nu_var = evalDMnuError(self.psrnoise.dnud,np.max(nus),np.min(nus))**2 / 25.0

        # PBF errors (scattering), included already in cov matrix?
        # Scattering error, assume this is proportional to nu^-4.4? or 4?
        chromatic_components = self.psrnoise.tauvar * np.power(nus,-4.4)
        #print chromatic_components
        scattering_var = np.dot(np.dot(np.dot(P,XT),VI),chromatic_components)[0,0]**2

        retval = np.sqrt(template_fitting_var + DM_nu_var + scattering_var)

        return retval




        
    def build_polarization_cov_matrix(self,epsilon=0.08,pi_V=0.1):
        W50s = self.psrnoise.W50s
        if type(W50s) != np.ndarray:
            W50s = np.zeros(self.nchan)+W50s
        if type(epsilon) != np.ndarray:
            epsilon = np.zeros(self.nchan)+epsilon
        if type(pi_V) != np.ndarray:
            pi_V = np.zeros(self.nchan)+pi_V

        sigmas = epsilon*pi_V*(W50s/100.0) #W50s in microseconds #do more?
        return np.matrix(np.diag(sigmas**2))



    def calc_single(self,nus):
        cov = self.build_template_fitting_cov_matrix(nus)#,Weffs=self.psrnoise.Weffs,alpha=self.psrnoise.alpha,beta=self.psrnoise.beta,A_e=self.psrnoise.A_e,I_0=self.psrnoise.I_0,taud=self.psrnoise.taud,EM=self.psrnoise.EM,T_e=self.psrnoise.T_e) 
        jittercov = self.build_jitter_cov_matrix()
        disscov = self.scintillation_noise(nus,self.psrnoise.dtd,taud0=self.psrnoise.taud) 
        cov = cov +jittercov + disscov
        sigma2 = epoch_averaged_error(cov,var=True)

        sigmatel2 = epoch_averaged_error(self.build_polarization_cov_matrix())

        sigma = np.sqrt(sigma2 + self.DM_misestimation(nus,cov,covmat=True)**2 + sigmatel2) #need to include PBF errors?

        return sigma


    def calc(self):
        self.sigmas = np.zeros((len(self.Cs),len(self.Bs)))
        if self.frac_bw == False:
            for ic,C in enumerate(self.Cs):
                if self.verbose:
                    print("Computing center freq %0.3f GHz (%i/%i)"%(C,ic,len(self.Cs)))
                for ib,B in enumerate(self.Bs):
                    if B > 1.9*C:
                        self.sigmas[ic,ib] = np.nan
                    else:
                        #C = 1.2
                        #B = 1.0
                        nulow = C - B/2.0
                        nuhigh = C + B/2.0
                        #print ic,len(self.Cs),C,B,nulow,nuhigh

                        if self.log == False:
                            nus = np.linspace(nulow,nuhigh,self.nchan+1)[:-1] #more uniform sampling?
                        else:
                            nus = np.logspace(np.log10(nulow),np.log10(nuhigh),self.nchan+1)[:-1] #more uniform sampling?   

                        self.sigmas[ic,ib] = self.calc_single(nus)
        else:
            for ic,C in enumerate(self.Cs):
                print(ic,len(self.Cs),C)
                for indf,F in enumerate(self.Fs):
                    #B = (2*C) * (R-1)/(R+1)
                    B = C*F
                    #print B
                    if B > 1.9*C or B <= 0:
                        self.sigmas[ic,indf] = np.nan
                    else:
                        nulow = C - B/2.0
                        nuhigh = C + B/2.0
                        #print "here",B,nulow,nuhigh,C,F
                        #print ic,len(self.Cs),C,B,nulow,nuhigh

                        if self.log == False:
                            nus = np.linspace(nulow,nuhigh,self.nchan+1)[:-1] #more uniform sampling?
                        else:
                            nus = np.logspace(np.log10(nulow),np.log10(nuhigh),self.nchan+1)[:-1] #more uniform sampling?   

                        self.sigmas[ic,indf] = self.calc_single(nus)



    def plot(self,filename="triplot.png",doshow=True,figsize=(8,6),save=True,minimum=None,points=None,colorbararrow=None):
        fig = figure(figsize=figsize)
        ax = fig.add_subplot(111)
        if self.frac_bw == False:
            data = np.transpose(np.log10(self.sigmas))
            if self.log == False:
                im = uimshow(data,extent=[self.Cs[0],self.Cs[-1],self.Bs[0],self.Bs[-1]],cmap=cm.inferno_r,ax=ax)

                ax.set_xlabel(r"$\mathrm{Center~Frequency~\nu_0~(GHz)}$")
                ax.set_ylabel(r"$\mathrm{Bandwidth}~B~\mathrm{(GHz)}$")
            else:

                im = uimshow(data,extent=np.log10(np.array([self.Cs[0],self.Cs[-1],self.Bs[0],self.Bs[-1]])),cmap=cm.inferno_r,ax=ax)
                cax = ax.contour(data,extent=np.log10(np.array([self.Cs[0],self.Cs[-1],self.Bs[0],self.Bs[-1]])),colors=COLORS,levels=LEVELS,linewidths=LWS,origin='lower')

                #https://stackoverflow.com/questions/18390068/hatch-a-nan-region-in-a-contourplot-in-matplotlib
                # get data you will need to create a "background patch" to your plot
                xmin, xmax = ax.get_xlim()
                ymin, ymax = ax.get_ylim()
                xy = (xmin,ymin)
                width = xmax - xmin
                height = ymax - ymin
                # create the patch and place it in the back of countourf (zorder!)
                p = patches.Rectangle(xy, width, height, hatch='X', color='0.75', fill=None, zorder=-10)
                ax.add_patch(p)


                ax.set_xlabel(r"$\mathrm{Center~Frequency~\nu_0~(GHz)}$")
                ax.set_ylabel(r"$\mathrm{Bandwidth}~B~\mathrm{(GHz)}$")
                ax.xaxis.set_major_formatter(noformatter)
                ax.yaxis.set_major_formatter(noformatter)

                ax.text(0.05,0.9,"PSR~%s"%self.psrnoise.name.replace("-","$-$"),fontsize=18,transform=ax.transAxes,bbox=dict(boxstyle="square",fc="white"))

            if minimum is not None:
                data = np.log10(self.sigmas)
                flatdata = data.flatten()
                inds = np.where(np.logical_not(np.isnan(flatdata)))[0]
                MIN = np.min(flatdata[inds])
                INDC,INDB = np.where(data==MIN)
                INDC,INDB = INDC[0],INDB[0]
                MINB = self.Bs[INDB]
                MINC = self.Cs[INDC]
                print("Minimum",MINC,MINB,MIN)
                if self.log:
                    ax.plot(np.log10(MINC),np.log10(MINB),minimum,zorder=50,ms=10)
                else:
                    ax.plot(MINC,MINB,minimum,zorder=50,ms=10)

            if points is not None:
                if type(points) == tuple:
                    points = [points]
                for point in points:
                    x,y,fmt = point
                    if self.log:
                        ax.plot(np.log10(x),np.log10(y),fmt,zorder=50,ms=8)
                    else:
                        ax.plot(x,y,fmt,zorder=50,ms=8)

            if colorbararrow is not None:
                data = np.log10(self.sigmas)
                flatdata = data.flatten()
                inds = np.where(np.logical_not(np.isnan(flatdata)))[0]
                MIN = np.min(flatdata[inds])
                MAX = np.max(flatdata[inds])
                if self.log == True:
                    x = np.log10(self.Cs[-1]*1.05)#self.Bs[-1])
                    dx = np.log10(1.2)#np.log10(self.Cs[-1])#self.Bs[-1]*2)
                    frac = (np.log10(colorbararrow)-MIN)/(MAX-MIN)
                    y = frac*(np.log10(self.Bs[-1]) - np.log10(self.Bs[0])) + np.log10(self.Bs[0])
                    #print MIN,MAX,colorbararrow
                    #print np.log10(self.Bs[-1]),np.log10(self.Bs[0]),frac,y
                    arrow(x,y,dx,0.0,fc='k',ec='k',zorder=50,clip_on=False)




        else:
            if self.log == False:
                pass
            else:
                goodinds = []
                for indf,F in enumerate(self.Fs):
                    if np.any(np.isnan(self.sigmas[:,indf])):
                        continue
                    goodinds.append(indf)
                goodinds = np.array(goodinds)
                data = np.transpose(np.log10(self.sigmas[:,goodinds]))

                im = uimshow(data,extent=np.log10(np.array([self.Cs[0],self.Cs[-1],self.Fs[goodinds][0],self.Fs[goodinds][-1]])),cmap=cm.inferno_r,ax=ax)
                cax = ax.contour(data,extent=np.log10(np.array([self.Cs[0],self.Cs[-1],self.Fs[goodinds][0],self.Fs[goodinds][-1]])),colors=COLORS,levels=LEVELS,linewidths=LWS,origin='lower')
                

                ax.set_xlabel(r"$\mathrm{Center~Frequency~\nu_0~(GHz)}$")
                #ax.set_ylabel(r"$r~\mathrm{(\nu_{max}/\nu_{min})}$")
                ax.set_ylabel(r"$\mathrm{Fractional~Bandwidth~(B/\nu_0)}$")
                ax.yaxis.set_major_locator(FixedLocator(np.log10(np.arange(0.25,1.75,0.25))))
                ax.xaxis.set_major_formatter(noformatter)
                ax.yaxis.set_major_formatter(noformatter2)
            
            
        cbar = fig.colorbar(im)#,format=formatter)
        cbar.set_label("$\mathrm{TOA~Uncertainty~\sigma_{TOA}~(\mu s)}$")

        # https://stackoverflow.com/questions/6485000/python-matplotlib-colorbar-setting-tick-formator-locator-changes-tick-labels
        cbar.locator = MultipleLocator(1)
        cbar.formatter = formatter
        '''
        MAX = np.max(data[np.where(np.logical_not(np.isnan(data)))])
        if MAX <= np.log10(700):
            cbar.formatter = formatter100
        else:
            cbar.formatter = formatter
        '''
        cbar.update_ticks()
        #if self.log:
        #    cb = colorbar(cax)



        if save:
            savefig(filename)
        if doshow:
            show()
        else:
            close()

    def save(self,filename):
        if self.frac_bw == False:
            np.savez(filename,Cs=self.Cs,Bs=self.Bs,sigmas=self.sigmas)
        else:
            np.savez(filename,Cs=self.Cs,Fs=self.Fs,sigmas=self.sigmas)




def run(psrnoise,numin=0.08,numax=10.0,nchan=60,log=True,nsteps=25,frac_bw=False,full_bandwidth=False,minimum=None,points=None,DIR="",arrowcalc=None,masks=None):
    freqopt = FrequencyOptimizer(psrnoise,numin=numin,numax=numax,nchan=nchan,log=log,nsteps=nsteps,frac_bw=frac_bw,full_bandwidth=full_bandwidth,masks=masks)
    freqopt.calc()
    if len(DIR) > 0 and DIR[-1] != "/":
        DIR += "/"
    if arrowcalc is not None:
        colorbararrow = freqopt.calc_single(arrowcalc)
    else:
        colorbararrow = None
    freqopt.plot("%s%s.png"%(DIR,psrnoise.name),doshow=False,minimum=minimum,points=points,colorbararrow=colorbararrow)
    freqopt.plot("%s%s.pdf"%(DIR,psrnoise.name),doshow=False,minimum=minimum,points=points,colorbararrow=colorbararrow)
    freqopt.save("%s%s.npz"%(DIR,psrnoise.name))
    inds = np.where(np.logical_not(np.isnan(freqopt.sigmas.flatten())))[0]
    #print np.min(freqopt.sigmas.flatten()[inds])
    return freqopt



if __name__ == '__main__':

    # J1713+0747
    # \Delta tau = tau variation = 11.9 ns at 1500 MHz -> 70.85 ns at 1 GHz. Divide by 2 = 35.425
    #47.6 minutes at 1.4 GHz from Jones et al.





    # where does EM=541.94 come from? The true value should be (15.99 pc cm^-3)**2 / (1180 pc) = 


    # AO: Gain of 10 K/Jy gives A_e = 2760 * 10 = 27600.0
    # GBT: Gain of 2 K/Jy? gives 2760 * 2 = 5520???




    NCHAN = 60

    '''
    psrnoiseJ1713AO = PulsarNoise("J1713+0747AO",alpha=1.2,beta=2.75,taud=52.1e-3,A_e=27600.0,I_0=10.323,EM=0.216,T_e=100,tauvar=35.4e-3,dtd=1754.8,Weffs=np.zeros(NCHAN)+550.0,sigma_Js=np.zeros(NCHAN)+0.039)
    run(psrnoiseJ1713AO)

    psrnoiseJ1713GBT = PulsarNoise("J1713+0747GBT",alpha=1.2,beta=2.75,taud=52.1e-3,A_e=5520.0,I_0=10.323,EM=0.216,T_e=100,tauvar=35.4e-3,dtd=1754.8,Weffs=np.zeros(NCHAN)+550.0,sigma_Js=np.zeros(NCHAN)+0.051)
    run(psrnoiseJ1713GBT)
    '''
    #raise SystemExit
    psrnoiseJ1909 = PulsarNoise("J1909-3744",alpha=1.89,beta=2.75,taud=28.2e-3,A_e=5520.0,I_0=2.64,EM=0.095,T_e=100,tauvar=20.8e-3,dtd=1386.1,Weffs=np.zeros(NCHAN)+250.0,sigma_Js=np.zeros(NCHAN)+0.014) #dtd = 1506.6 from Lina's paper?, slight change in taud (29.2 versus 28.2?)
    run(psrnoiseJ1909,full_bandwidth=True)
    raise SystemExit
    '''
    psrnoiseJ1643 = PulsarNoise("J1643-1224",alpha=2.23,beta=2.75,taud=50.7,A_e=5520.0,I_0=9.127,EM=5.26,T_e=100,tauvar=None,dtd=357.9,Weffs=np.zeros(NCHAN)+1000.0,sigma_Js=np.zeros(NCHAN)+0.219) 
    run(psrnoiseJ1643)#,nsteps=100,frac_bw=True)
    '''

    '''

    psrnoiseB1937 = PulsarNoise("B1937+21",alpha=2.32,beta=2.75,taud=0.39,A_e=5520.0,I_0=28.767,EM=1.44,T_e=100,tauvar=224.0e-3,dtd=201.0,Weffs=np.zeros(NCHAN)+150.0,sigma_Js=np.zeros(NCHAN)+0.0096) #GBT!
    run(psrnoiseB1937)
    '''

    
    psrnoiseJ1903 = PulsarNoise("J1903+0327",alpha=2.08,beta=2.75,taud=633.9,A_e=5520.0,I_0=2.614,EM=47.6,T_e=100,tauvar=None,dtd=7.405,Weffs=np.zeros(NCHAN)+350.0,sigma_Js=np.zeros(NCHAN)+0.257) 
    run(psrnoiseJ1903,nsteps=100)
    
    
    #psrnoiseJ0645 = PulsarNoise("J0645+5158",alpha=1.69,beta=2.75,taud=36.3e-3,A_e=5520.0,I_0=0.512,EM=0.416,T_e=100,tauvar=None,dtd=480.8,Weffs=np.zeros(NCHAN)+600.0,sigma_Js=np.zeros(NCHAN)+0.087)  #jitter upper limit
    #run(psrnoiseJ0645)#,nsteps=100,frac_bw=True)
    #'''
    # B1855+09?
    #'''
    psrnoiseJ1744 = PulsarNoise("J1744-1134",alpha=1.49,beta=2.75,taud=26.1e-3,A_e=5520.0,I_0=4.888,EM=0.025,T_e=100,tauvar=0.344e-3,dtd=1272.2,Weffs=np.zeros(NCHAN)+512.0,sigma_Js=np.zeros(NCHAN)+0.066)  #jitter upper limit
    run(psrnoiseJ1744)#,nsteps=100,frac_bw=True)
    raise SystemExit


    '''
    psrnoiseJ0437 = PulsarNoise("J0437-4715",alpha=1.04,beta=2.75,dnud=0.168,A_e=5520.0,I_0=211.6,EM=0.0437,T_e=100,tauvar=None,dtd=1528.2,Weffs=np.zeros(NCHAN)+537.2,sigma_Js=np.zeros(NCHAN)+0.038)  #A_e is that of GBT
    run(psrnoiseJ0437)
    '''
    #raise SystemExit



    NCHAN = 60
    NSTEPS = 100
    #'''
    psrnoiseJ1713GBT = PulsarNoise("J1713+0747GBT1",alpha=1.2,beta=2.75,taud=52.1e-3,A_e=5520.0,I_0=10.323,EM=0.216,T_e=100,tauvar=35.4e-3,dtd=1754.8,Weffs=np.zeros(NCHAN)+550.0,sigma_Js=np.zeros(NCHAN)+0.051)
    run(psrnoiseJ1713GBT,nsteps=NSTEPS)#,frac_bw=True)

    psrnoiseJ1713GBT = PulsarNoise("J1713+0747GBT2",alpha=1.2,beta=2.75,taud=52.1e-3,A_e=2*5520.0,I_0=10.323,EM=0.216,T_e=100,tauvar=35.4e-3,dtd=1754.8,Weffs=np.zeros(NCHAN)+550.0,sigma_Js=np.zeros(NCHAN)+0.051)
    run(psrnoiseJ1713GBT,nsteps=NSTEPS)#,frac_bw=True)

    psrnoiseJ1713GBT = PulsarNoise("J1713+0747GBT5",alpha=1.2,beta=2.75,taud=52.1e-3,A_e=5*5520.0,I_0=10.323,EM=0.216,T_e=100,tauvar=35.4e-3,dtd=1754.8,Weffs=np.zeros(NCHAN)+550.0,sigma_Js=np.zeros(NCHAN)+0.051)
    run(psrnoiseJ1713GBT,nsteps=NSTEPS)#,frac_bw=True)

    psrnoiseJ1713GBT = PulsarNoise("J1713+0747GBT10",alpha=1.2,beta=2.75,taud=52.1e-3,A_e=10*5520.0,I_0=10.323,EM=0.216,T_e=100,tauvar=35.4e-3,dtd=1754.8,Weffs=np.zeros(NCHAN)+550.0,sigma_Js=np.zeros(NCHAN)+0.051)
    run(psrnoiseJ1713GBT,nsteps=NSTEPS)#,frac_bw=True)
    raise SystemExit
    #'''

    '''
    psrnoiseJ1643VLA = PulsarNoise("VLA_J1643-1224",alpha=2.23,beta=2.75,taud=50.7,A_e=5520.0,I_0=9.127,EM=5.26,T_e=100,tauvar=None,dtd=357.9,Weffs=np.zeros(NCHAN)+1000.0,sigma_Js=np.zeros(NCHAN)+0.219) 
    freqopt = run(psrnoiseJ1643VLA,numin=1.0,nsteps=100,frac_bw=True)
    '''

    #'''
    psrnoiseJ2317GBT = PulsarNoise("J2317+1439GBT",alpha=1.26,beta=2.75,taud=26.3e-3,A_e=5520.0,I_0=5.615,EM=0.335,T_e=100,tauvar=6.25e-3,dtd=499.4,Weffs=np.zeros(NCHAN)+390.0,sigma_Js=np.zeros(NCHAN)+0.084)
    run(psrnoiseJ2317GBT,nchan=NCHAN,nsteps=NSTEPS)
    psrnoiseJ2317AO = PulsarNoise("J2317+1439AO",alpha=1.26,beta=2.75,taud=26.3e-3,A_e=5*5520.0,I_0=5.615,EM=0.335,T_e=100,tauvar=6.25e-3,dtd=499.4,Weffs=np.zeros(NCHAN)+390.0,sigma_Js=np.zeros(NCHAN)+0.084)
    run(psrnoiseJ2317AO,nchan=NCHAN,nsteps=NSTEPS)
    raise SystemExit
    #'''

    '''
    #flux index = 0.32?
    psrnoiseJ1944GBT = PulsarNoise("J1944+0907GBT",alpha=1.4,beta=2.75,taud=103.8e-3,A_e=5520.0,I_0=2.899,EM=0.436,T_e=100,tauvar=69.1e-3,dtd=1109.0,Weffs=np.zeros(NCHAN)+420.0,sigma_Js=np.zeros(NCHAN)+0.277)
    run(psrnoiseJ1944GBT,nchan=NCHAN,nsteps=NSTEPS)#,log=False)#,nsteps=NSTEPS)
    psrnoiseJ1944AO = PulsarNoise("J1944+0907AO",alpha=1.4,beta=2.75,taud=103.8e-3,A_e=5*5520.0,I_0=2.899,EM=0.436,T_e=100,tauvar=69.1e-3,dtd=1109.0,Weffs=np.zeros(NCHAN)+420.0,sigma_Js=np.zeros(NCHAN)+0.277)
    run(psrnoiseJ1944AO,nchan=NCHAN,nsteps=NSTEPS)#,log=False)#,nsteps=NSTEPS)
    '''


    raise SystemExit
    #'''
    psrnoiseJ1640GBT = PulsarNoise("J1640+2224GBT",alpha=1.73,beta=2.75,taud=19.5e-3,A_e=5520.0,I_0=2.531,EM=0.226,T_e=100,tauvar=8.5e-3,dtd=635.5,Weffs=np.zeros(NCHAN)+420.0,sigma_Js=np.zeros(NCHAN)+0.168)
    run(psrnoiseJ1640GBT,nsteps=NSTEPS,nchan=NCHAN)
    psrnoiseJ1640AO = PulsarNoise("J1640+2224AO",alpha=1.73,beta=2.75,taud=19.5e-3,A_e=5*5520.0,I_0=2.531,EM=0.226,T_e=100,tauvar=8.5e-3,dtd=635.5,Weffs=np.zeros(NCHAN)+420.0,sigma_Js=np.zeros(NCHAN)+0.168)
    run(psrnoiseJ1640AO,nsteps=NSTEPS,nchan=NCHAN)
    #'''
    #raise SystemExit
    psrnoiseJ0030GBT = PulsarNoise("J0030+0451GBT",alpha=2.12,beta=2.75,taud=0.8e-3,A_e=5520.0,I_0=1.903,EM=0.052,T_e=100,dtd=6189.3,Weffs=np.zeros(NCHAN)+600.0,sigma_Js=np.zeros(NCHAN)+0.216)
    run(psrnoiseJ0030GBT,nsteps=NSTEPS)
    psrnoiseJ0030AO = PulsarNoise("J0030+0451AO",alpha=2.12,beta=2.75,taud=0.8e-3,A_e=5*5520.0,I_0=1.903,EM=0.052,T_e=100,dtd=6189.3,Weffs=np.zeros(NCHAN)+600.0,sigma_Js=np.zeros(NCHAN)+0.216)
    run(psrnoiseJ0030AO,nsteps=NSTEPS)