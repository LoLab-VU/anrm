# Datatools 1.0 (Irvin et. al 2013) Handles Non-Quantitative Data for ANRM

import math
import numpy as np
import itertools as itr
import multiprocessing as mp
import calibratortools as ct

from scipy import stats
from scipy.optimize import minimize_scalar
from copy import deepcopy
from collections import Counter, defaultdict
import datetime as dt
start = dt.datetime.now()
class Data:
    def __init__(self, data_dict):
        self.exp_name = data_dict['Experiment_Name']
        self.con_name = data_dict['Condition_Name']
        self.initials = eval(data_dict['Initial_Condition'])
        self.type = data_dict['Type']
        self.observable = data_dict['Observable']
        self.observation = data_dict['Observation']
        self.ordrank = [i.strip() for i in data_dict['Category_Rank'].split(',')]
        self.partition = eval(data_dict['Partition'])
        self.adj_observation = data_dict['Adjusted_Observation']
        self.tspan = None
        self.obs_func = None
        self.obs_func_input = None
        if data_dict['Observable_Transformation']:
            if len(data_dict['Observable_Transformation'].split(',')) is 1:
                self.obs_func = getattr(ct, data_dict['Observable_Transformation'])
            
            else:
                self.obs_func = getattr(ct, data_dict['Observable_Transformation'].split(',')[0])
                self.obs_func_input = eval(data_dict['Observable_Transformation'][data_dict['Observable_Transformation'].find(',')+1:])
    
        self.ysim = None
        self.normalize = None
        if data_dict['Normalize_Option']:
            self.normalize = eval(data_dict['Normalize_Option'])
        self.y_list = []
        
    def assign_obs_values(self):
        #Chect to see that ysims, xsims not None
        self.signal = ct.extract_records(self.ysim, [i.strip() for i in self.observable.split(',')])
        if self.normalize:
            self.signal = ct.normalize(self.signal, option = self.normalize)
    
        if self.obs_func_input:
            if self.type == 'Quantitative':
                print max(self.signal)
            return self.obs_func(self.signal, self.obs_func_input, self.tspan)
        else:
            return self.obs_func(self.signal, self.tspan)

class Analysis(object):
    def __init__(self, options, data_list):
        self.options = options.copy()
        self.data_list = data_list

    def initialize(self):
        self.expand_list(self.data_list)
        self.cond_names, self.conditions = self.conditions_list(self.data_list)
    
    def run(self):
        self.model_outputs()
        self.scale_data(self.data_list)
        #self.reset_ylist(self.data_list) #growing list of y for computing variances
    
    def expand_list(self, data_list):
        """Time course data is imported as a list of timepoints and observations. These data
        need to be reassigned as their own individual data classes in our data_list"""
        ratchetdata = []
        for d in data_list:
            d.tspan = self.options.options.tspan
            if d.obs_func ==  ct.timepoints and len(d.obs_func_input)>1:
                inputs = deepcopy(d.obs_func_input)
                observations = deepcopy(d.observation)
                d.obs_func_input = [inputs[0]]
                d.observation = observations.split(',')[0].strip()
                
                for i in range(len(inputs[1:])):
                    new_datum = deepcopy(d)
                    new_datum.obs_func_input = [inputs[i+1]]
                    new_datum.observation = observations.split(',')[i+1].strip()
                    ratchetdata.append(new_datum)
        data_list.extend(ratchetdata)

    def conditions_list(self, data_list):
        condnames = {}
        for d in data_list:
            condnames[d.con_name] = d.initials

        conditions = {k: ct.initial_conditions(v.keys(), v.values(), self.ic_params)
                for k, v in condnames.items()}
        return condnames, conditions
    def reset_ylist(self):
        for d in self.data_list:
            d.y_list = []

    def model_outputs(self):
        ysims = {}
        if self.multiprocess:
            print "model outputs", dt.datetime.now() - start

            num_procs = min(mp.cpu_count()-1, len(self.conditions))
            iterate_args = [(k,v) for k, v in self.conditions.iteritems()]
            ysim_list = parmap(lambda i: self.get_ysim(i), iterate_args, nprocs=num_procs)
            for i in range(len(ysim_list)):
                ysims[iterate_args[i][0]] = ysim_list[i]
    
        else:
            for k in self.cond_names.keys():
                ysims[k] = deepcopy(self.options.simulate(self.position, observables=True, initial_conc=self.conditions[k]))
        
        for d in self.data_list:
            d.ysim = ysims[d.con_name]
            d.modelout = d.assign_obs_values()
            d.y_list.extend(d.modelout)

    def get_ysim(self, condition):
        return deepcopy(self.options.simulate(self.position, observables = True, initial_conc = condition[1]))
    
    def create_iterator(self, datalist):
        types = Counter([d.type for d in datalist])
        observables = Counter([d.observable for d in datalist])
        obs_funcs = Counter([d.obs_func for d in datalist])
        partitions = Counter([d.partition for d in datalist])
        
        iterator = []
        for i in types:
            for j in observables:
                for k in obs_funcs:
                    for l in partitions:
                        iterator.append((i, j, k, l))
        return iterator
    
    def scale_data(self, datalist):
        print "scale data", dt.datetime.now() - start
        for iterator in self.create_iterator(datalist):
            trimmed_data =  self.trim_data(datalist, type=iterator[0], observable=iterator[1], obs_func=iterator[2], partition=iterator[3])
            if trimmed_data:
                self.scaled_data = self.optimal_scale(trimmed_data, type=iterator[0])

    def trim_data(self, data_list, type =None, observable = None, partition = None, obs_func = None, obs_func_input = None):
        """trim data to include only those being optimally scaled"""
        if not (type and observable):
            raise Exception("Please provide type and observable to trim the data set by")
        for d in data_list:
            trimmed_data = [(i,d) for i, d in enumerate(data_list) if (d.type == type and d.observable == observable)]
        if partition:
            td = [(i,d) for (i,d) in trimmed_data if d.partition == partition]
            trimmed_data = td
        else:
            td = [(i,d) for (i,d) in trimmed_data if d.partition == trimmed_data[0][1].partition]
            trimmed_data = td
        if obs_func:
            td = [(i,d) for (i,d)in trimmed_data if d.obs_func == obs_func]
            trimmed_data = td
        else:
            td = [(i,d) for (i,d) in trimmed_data if d.obs_func == trimmed_data[0][1].obs_func]
            trimmed_data = td
        if obs_func_input:
            td = [(i,d) for (i,d) in trimmed_data if d.obs_func_input == obs_func_input]
            trimmed_data = td
            # Not using "else:" because we can compare data from different timepoints etc..
        return trimmed_data

    def indicate_matrix(self, datalist):
        categories = self.get_categories(datalist)
        indicator_matrix = np.zeros((len(categories),len(datalist)))
        if self.contains(datalist, lambda x: x[1].adj_observation):
            for i in range(len(datalist)):
                indicator_matrix[categories.index(datalist[i][1].adj_observation),i] = 1
        else:
            for i in range(len(datalist)):
                indicator_matrix[categories.index(datalist[i][1].observation),i] = 1
        return np.asmatrix(indicator_matrix).T

    def get_categories(self, datalist):
        if self.contains(datalist, lambda x: x[1].adj_observation):
            categories = [d.adj_observation for (i,d) in datalist]
            categories = Counter(categories).keys()
        else:
            categories = [d.observation for (i,d) in datalist]
            categories = Counter(categories).keys()

        return categories

    def contains(self, data_list, filter):
        for x in data_list:
            if filter(x):
                return True
        return False

    def optimal_scale(self, datalist, type=None):
        if type == 'Nominal':
            return self.optimal_scale_nominal(datalist, 'Nominal')
        if type == 'Ordinal':
            return self.optimal_scale_ordinal(datalist)
        if type == 'Quantitative':
            return self.quantitative_data(datalist)

    def quantitative_data(self, datalist):
        z_scaled = [float(d.observation) for (i,d) in datalist]
        for i in range(len(datalist)):
            datalist[i][1].z_scaled = np.asmatrix([z_scaled[i]])

    def optimal_scale_nominal(self, datalist, type = None):
        self.indicator_matrix = self.indicate_matrix(datalist)
        U = self.indicator_matrix
        z = [d.modelout for (i,d) in datalist]
        z_scaled = U*np.matrix.getI(U.T*U)*U.T*z
        if type == 'Nominal':
            y_lists  = [d[1].y_list for d in datalist]
            z_scaled = self.add_gaps(z_scaled, y_lists)
                                
        for i in range(len(datalist)):
            if z_scaled[i]<0:
                datalist[i][1].z_scaled = np.asmatrix([0.])
            else:
                datalist[i][1].z_scaled = z_scaled[i]

        return datalist

    def optimal_scale_ordinal(self, datalist):
        scaled_datalist = self.optimal_scale_nominal(datalist)
        ordereddata = sorted(scaled_datalist, key=lambda x: x[1].ordrank.index(x[1].observation))
        #generate new categories so that the largest term each category is smaller than the smallest term in higher ranked categories.
        cat = {}
        j = 0
        cat[j] = [ordereddata[0]]
        for i in range(len(ordereddata)-1):
            catlow  = [d[1].z_scaled for d in ordereddata[:i+1]]
            cathigh = [d[1].z_scaled for d in ordereddata[i+1:]]
            if max(catlow)<min(cathigh):
                j+=1
                cat[j] = []
            cat[j].append(ordereddata[i+1])

        z = [d.modelout for (i,d) in ordereddata]
        U = np.zeros((len(cat),len(datalist)))#new indicator matrix
        vidx = 0
        for j in range(len(cat)):
            for i in range(len(cat[j])):
                U[j,i+vidx] = 1
            vidx+=i+1
        
        U = np.asmatrix(U).T
        z = np.asmatrix(z)
        

        z_scaled = U*np.matrix.getI(U.T*U)*U.T*z
        y_lists  = [d.y_list for (i,d) in ordereddata]
        z_scaled = self.add_gaps(z_scaled, y_lists)

        for i in range(len(ordereddata)):
            if z_scaled[i]<0:
                ordereddata[i][1].z_scaled = np.asmatrix([0.])
            else:
                ordereddata[i][1].z_scaled = z_scaled[i]
            
            print (ordereddata[i][1].exp_name, ordereddata[i][1].con_name,ordereddata[i][1].observation, ordereddata[i][1].observable, ordereddata[i][1].modelout, ordereddata[i][1].z_scaled)

    def add_gaps(self, z_scaled, y_lists):
        if len(y_lists[0]) < 2:
            return z_scaled
        z_scaled = [round(i, 3) for i in z_scaled]
        
        if type == 'Nominal':
            p_value = 0.025 #two tailed test for x1 =! x2
        else:
            p_value = 0.05 #one tailed test for x1 < x2 (i.e. ordinal)

        z_idx = [(v, i, y_lists[i]) for (i,v) in enumerate(z_scaled)]
        cat_dict = defaultdict(list)
        for k,i,v in z_idx:
            cat_dict[k].extend(v)
        
        cat_vars = sorted([(z, np.var(y), len(y)) for (z, y) in cat_dict.items()])
        
        if len(cat_vars) <= 1:
            return [np.array(i) for i in z_scaled]
        
        dof = [self.Welch_Satterthwaite_Eq([cat_vars[i][1],cat_vars[i+1][1]], [cat_vars[i][2],cat_vars[i+1][2]]) for i in range(len(cat_vars[:-1]))] #degrees of freedom for Welch's t- test.
        tstat = [stats.t.ppf(1-p_value, df) for df in dof]
        pvars = [self.Pooled_Variance([cat_vars[i][1],cat_vars[i+1][1]], [cat_vars[i][2],cat_vars[i+1][2]]) for i in range(len(cat_vars[:-1]))]
        catgaps = [tstat[i]*pvars[i] for i in range(len(tstat))]

        z_gaps = self.z_with_gaps(catgaps, cat_vars)
        gaps = [(cat_vars[i][0], z_gaps[i]) for i in range(len(z_gaps))]
        gaps_dict = dict(gaps)
        
        new_z_scaled = []
        for i in z_scaled:
            new_z_scaled.append(np.array(gaps_dict[i]))
        return new_z_scaled

    def Welch_Satterthwaite_Eq(self, var, num):
        return ((var[0]/num[0] + var[1]/num[1])**2)/((((var[0]/num[0])**2)/(num[0]-1)) + (((var[0]/num[0])**2)/(num[0]-1)))
        
    def Pooled_Variance(self, var, num):
        return np.sqrt((var[0]/num[0]) + (var[1]/num[1]))

    def z_with_gaps(self, catgaps, cat_vars):
        for i in range(len(catgaps)):
            if math.isnan(catgaps[i]):
                catgaps[i] = 0
        
        b  = [max(catgaps[i],(cat_vars[i+1][0]-cat_vars[i][0])) for i in range(len(catgaps))]

        a  = [i[0] for i in cat_vars]
        x_optimized = minimize_scalar(self.residuals, args = (a, b))
        x_opt = round(x_optimized.x, 3)

        gaps = [x_optimized.x]
        gaps_remaining = [x_opt+ np.sum(b[:i+1]) for i in range(len(b))]
        gaps.extend(gaps_remaining)
        return gaps
        
    def residuals(self, x, a, b):
        bx_rem = [x+ np.sum(b[:i+1]) for i in range(len(b))]
        bx  = [x]
        bx.extend(bx_rem)
        bx = np.array(bx).T
        a  = np.array(a)
        return sum([i**2 for i in a-bx])

def fun(f,q_in,q_out):
    while True:
        i,x = q_in.get()
        
        if i is None:
            break
        q_out.put((i,f(x)))

def parmap(f, X, nprocs = mp.cpu_count()):
    q_in   = mp.Queue(1)
    q_out  = mp.Queue()
    
    proc = [mp.Process(target=fun,args=(f,q_in,q_out)) for _ in range(nprocs)]
    for p in proc:
        p.daemon = True
        p.start()
    
    sent = [q_in.put((i,x)) for i,x in enumerate(X)]
    [q_in.put((None,None)) for _ in range(nprocs)]
    res = [q_out.get() for _ in range(len(sent))]
    [p.join() for p in proc]
    return [x for i,x in sorted(res)]

"""Options for defining a bayessb.MCMC project/run.
    
    Constructor takes no options. Interface is via direct manipulation of
    attributes on instances.
    
    Attributes
    ----------
    model : pysb.Model (or similar)
    The model to estimate. If you do not wish to use a PySB model, you may
    instead provide any object with a `parameters` attribute holding a list
    of all model parameters. The parameter objects in turn must each have a
    `value` attribute containing the parameter's numerical value. If you are
    not using a PySB model you must rely on your own code to simulate the
    model in your likelihood function instead of calling `MCMC.simulate`.
    estimate_params : list of pysb.Parameter
    List of parameters to estimate, all of which must also be listed in
    `model.parameters`.
    initial_values : list of float, optional
    Starting values for parameters to estimate. If omitted, will use the
    nominal values from `model.parameters`.
    tspan : list of float
    List of time points over which to integrate the model. Ignored if not
    using a PySB model.
    start_random : bool, optional
    Whether to start from a random point in parameter space. Defaults to
    false. (NOT IMPLEMENTED)
    boundary_option : bool, optional
    Whether to enforce hard boundaries on the walk trajectory. Defaults to
    false. (NOT IMPLEMENTED)
    rtol : float or list of float, optional
    Relative tolerance for ODE solver.
    atol : float or list of float, optional
    Absolute tolerance for ODE solver.
    
    """

