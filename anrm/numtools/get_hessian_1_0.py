# Fits ANRM 1.0 (Irvin et. al 2013) against single-cell measurements
# of caspase reporters.

import pickle
import bayessb
import random as ra 
import numpy as np
import calibratortools as ct
import simulator_1_0 as sim
import bayes_mcmc as bmc
import matplotlib.pyplot as plt

from anrm.irvin_mod_v5_wo_po4bid import model

#----Experiment Name--------
Exp_name = ('CompII_Hyp_123_Bid_Hyp_0_Apop1_Apop2_Necr1')
print Exp_name

#----Data and conditions----
#init_conc = {'Apop1':{'TNFa_0': 600}}
#init_conc = {'Apop2':{'TNFa_0': 1200}}
#init_conc = {'Necr1':{'TNFa_0':1800, 'zVad_0':9.6e6, 'FADD_0':0}}

#init_conc = {'Apop2':{'TNFa_0': 1200}, 'Necr1':{'TNFa_0':1800, 'zVad_0':9.6e6, 'FADD_0':0}}
#init_conc = {'Apop1':{'TNFa_0': 600}, 'Apop2':{'TNFa_0': 1200}}
init_conc = {'Apop1':{'TNFa_0': 600}, 'Apop2':{'TNFa_0': 1200}, 'Necr1':{'TNFa_0':1800, 'zVad_0':9.6e6, 'FADD_0':0}} #600 = 10ng/ml TNFa, 9.6e6 = 20uM

#----Experimental Data----
"""
    ydata: dict keys = name of the experimental conditions. The items in the dict are 1x2 lists
    the first item in the list is an array of data.
    Array[:,0,:] = timepoints
    array[:,1,:] = values
    array[:,2,:] = variance
    the 3rd dimension is the observables.
    the second item in the list is the observables.
    
    init_conc: dict of experimental conditions(keys) and initial mononmer concentrations (items)
    objective_fn:
    prior:
    step:
"""
#-----------Previously Calibrated Parameters------------
initial_position = pickle.load(open('CompII_Hyp_123_Bid_Hyp0_newtopology_1run_v4_Position.pkl'))

#----User Defined Functions-----
def ydata_fn():
    """return and array of synthesized experimental data. The array is loosely based on published experiments"""
    Apop1_td = 6.0 #six hours
    Apop2_td = 4.0 #four hours
    Necr1_td = 4.0 #four hours

    switchtime_CytoC = 1.0 # [hrs]
    switchtime_cPARP = 0.5 #one hour
    switchtime_MLKL = 1.0 # [hrs]

    Apop1_obs = ['Obs_CytoC'] #Zhang et al. Monitored CytoC (Obs_CytoC) but CytoC does not have switch behavior.
    Apop2_obs = ['Obs_cPARP']
    Necr1_obs = ['Obs_MLKL']
    
    ydata = {}
    ydata['Apop1'] = [np.array([[(Apop1_td-2*switchtime_CytoC),(Apop1_td-switchtime_CytoC), (Apop1_td-switchtime_CytoC/2), (Apop1_td-switchtime_CytoC/4), (Apop1_td-switchtime_CytoC/8), Apop1_td, (Apop1_td+switchtime_CytoC/8), (Apop1_td+switchtime_CytoC/4), (Apop1_td+switchtime_CytoC/2), (Apop1_td+switchtime_CytoC)], [0, 0, 0.05, 0.205, 0.340, 0.5, 0.659, 0.794, 0.95, 1],[0.025, 0.025, 0.025, 0.05, 0.075, 0.1, 0.085, 0.065, 0.05, 0.025]]).T, Apop1_obs]
    ydata['Apop2'] = [np.array([[(Apop2_td-2*switchtime_cPARP),(Apop2_td-switchtime_cPARP), (Apop2_td-switchtime_cPARP/2), (Apop2_td-switchtime_cPARP/4), (Apop2_td-switchtime_cPARP/8), Apop2_td, (Apop2_td+switchtime_cPARP/8), (Apop2_td+switchtime_cPARP/4), (Apop2_td+switchtime_cPARP/2), (Apop2_td+switchtime_cPARP)], [0, 0, 0.05, 0.205, 0.340, 0.5, 0.659, 0.794, 0.95, 1], [0.025, 0.025, 0.025, 0.05, 0.075, 0.1, 0.085, 0.065, 0.05, 0.025]]).T, Apop2_obs]
    ydata['Necr1'] = [np.array([[(Necr1_td-2*switchtime_MLKL),(Necr1_td-switchtime_MLKL), (Necr1_td-switchtime_MLKL/2), (Necr1_td-switchtime_MLKL/4), (Necr1_td-switchtime_MLKL/8), Necr1_td, (Necr1_td+switchtime_MLKL/8), (Necr1_td+switchtime_MLKL/4), (Necr1_td+switchtime_MLKL/2), (Necr1_td+switchtime_MLKL)], [0, 0, 0.05, 0.205, 0.340, 0.5, 0.659, 0.794, 0.95, 1], [0.025, 0.025, 0.025, 0.05, 0.075, 0.1, 0.085, 0.065, 0.05, 0.025]]).T, Necr1_obs]
    
    return ydata

def objective_fn_simple(position):
    """return the value of the objective function"""
    objective = []
    for k in conditions.keys():
        ysim = solve.simulate(position, observables=True, initial_conc=conditions[k])
        ysim_array = ct.extract_records(ysim, ynorm[k][1])
        ysim_norm  = ct.normalize(ysim_array, option = 1)
        ysim_tp    = ct.cubic_spline(solve.options.tspan, ysim_norm, ynorm[k][0][:,0]*3600)

        objective.append(np.sum((ynorm[k][0][:,1] - ysim_tp) ** 2 / (2 * ynorm[k][0][:,2])))
    return np.sum(objective)

def objective_fn(position):
    """return the value of the objective function"""
    objective = []
    for k in conditions.keys():
        ysim = solve.simulate(position, observables=True, initial_conc=conditions[k])
        PARP_MLKL_signals   = ct.extract_records(ysim, ['Obs_cPARP', 'Obs_MLKL'])
        
        if (k == 'BidKO'):
            if max(PARP_MLKL_signals[0]>0):
                td_PARP = ct.calculate_time_delay(PARP_MLKL_signals[:,0], sims.tspan)
                td_MLKL = ct.calculate_time_delay(PARP_MLKL_signals[:,1], sims.tspan)
                if td_PARP < td_MLKL:
                    objective.append(abs(td_PARP - td_MLKL))
    
        else:
            ysim_array = ct.extract_records(ysim, ynorm[k][1])
            ysim_norm  = ct.normalize(ysim_array, option = 1)
            ysim_tp    = ct.cubic_spline(solve.options.tspan, ysim_norm, ynorm[k][0][:,0]*3600)
        
            if (k == 'Necr1'):
                objective.append(np.sum((ynorm[k][0][:,1] - ysim_tp) ** 2 / (2 * ynorm[k][0][:,2])))
        
            else:
                td_PARP = ct.calculate_time_delay(PARP_MLKL_signals[:,0], sims.tspan)
                td_MLKL = ct.calculate_time_delay(PARP_MLKL_signals[:,1], sims.tspan)
                if td_MLKL < td_PARP:
                    objective.append(np.sum((ynorm[k][0][:,1] - ysim_tp) ** 2 / (2 * ynorm[k][0][:,2]))+abs(td_PARP - td_MLKL))
                else:
                    objective.append(np.sum((ynorm[k][0][:,1] - ysim_tp) ** 2 / (2 * ynorm[k][0][:,2])))

    return np.sum(objective)
    

def calculate_time_delay(signal):
    if np.isnan(np.sum(signal)):
        return None
    else:
        norm_signal = ct.normalize(signal, option = 0)
        norm_signal = norm_signal.tolist()
        idx         = norm_signal.index(min(norm_signal, key = lambda x: abs(x-0.5)))
        return ct.cubic_spline(norm_signal[idx-3:idx+3], solve.options.tspan[idx-3:idx+3], [0.5], degree = 1)
    
def prior(mcmc, position):
    """Distance to original parameter values"""
    
    return np.sum((position - prior_ln_mean) ** 2 / ( 2 * prior_var))

#----Data and conditions----
ydata = ydata_fn()


#----Normalize--------------
ynorm = ydata.copy()
normalize = ct.normalize_array
for k in ynorm.keys():
    ynorm[k] = [normalize(ynorm[k][0], option = 1), ynorm[k][1]]

#----Initial Protein Concetrations----
conditions = {}
ic_params  = model.parameters_initial_conditions()
for k in init_conc.keys():
    conditions[k] = ct.initial_conditions(init_conc[k].keys(), init_conc[k].values(), ic_params)

#----Simulator Settings----
sims = sim.Settings()
sims.model = model
sims.tspan = np.linspace(0,36000,1000) #10hrs converted to seconds (1000 timepoints)
sims.estimate_params = model.parameters_rules()
sims.rtol = 1e-5
sims.atol = 1e-5

solve = sim.Solver(sims)
solve.run()

#----Bayesian and MCMC Options----
opts = bmc.MCMCOpts()
opts.nsteps = 3000
opts.likelihood_fn = objective_fn_simple
opts.prior_fn = prior
opts.seed = ra.randint(0,1000)
#opts.initial_values = np.power(10, initial_position)
opts.initial_values = solve.initial_values
opts.initial_conc = conditions
opts.T_init = 10

# values for prior calculation
prior_mean = [p.value for p in solve.options.estimate_params]
prior_ln_mean = np.log10(prior_mean)
prior_var = 6.0

mcmc = bmc.MCMC(opts)

mcmc.num_estimate = len(opts.initial_values)
mcmc.position = initial_position
hess = mcmc.calculate_hessian()

pickle.dump(hess, open('pysb_hessian_%s.pkl' % Exp_name, 'wb'))

