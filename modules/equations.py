reset_e_no_theta = 'v = v_reset_e'
# theta increases by a fixed amount on each spike
reset_e_theta = reset_e_no_theta + '''
theta = clip(theta + theta_coef * mV, min_theta, max_theta)
'''
# theta increases proportionally to distance from max_theta
reset_e_adapting_theta_exp = reset_e_no_theta + '''
theta = theta + theta_coef * (max_theta - theta)
'''
# theta increases by theta_mod, which decays exponentially
reset_e_adapting_theta_noexp = reset_e_no_theta + '''
theta = theta + theta_coef * theta_mod * mV
theta_mod *= 0.8
'''
# theta increases proportionally to distance from max_ge
reset_e_ge_theta = reset_e_no_theta + '''
max_ge = int(ge > max_ge) * ge + int(max_ge >= ge) * max_ge
theta = theta + theta_coef * ((45 + max_ge/nS) * mV - theta)
'''

thresh_e = 'v > (theta - offset + v_thresh_e)'

neuron_eqs = '''
I_synE = ge * (e_ex - v) : amp
I_synI = gi * (e_in - v) : amp
dge/dt = -ge / tc_ge     : siemens
dgi/dt = -gi / tc_gi     : siemens
'''

# dv/dt describes the rate of change of membrane potential
# 1. 'v_rest - v' pulls v towards v_rest
# 2. 'ge * (0 - v)' pulls v towards 0, proportionally to ge
# 3. 'ge * (-100 - v)' pulls v towards -100, proportionally to gi
neuron_eqs_e = neuron_eqs + '''
dv/dt = ((v_rest - v) + (I_synE + I_synI) * 1 * ohm) / tc_v : volt (unless refractory)
dtheta/dt = -theta / (tc_theta)                             : volt
theta_mod                                                   : 1
max_ge                                                      : siemens
x                                                           : 1
y                                                           : 1
'''

reset_i = 'v = v_reset_i'
thresh_i = 'v > v_thresh_i'

neuron_eqs_i = neuron_eqs + '''
dv/dt = ((v_rest - v) + (I_synE + I_synI) * 1 * ohm) / tc_v : volt
'''

# TODO: add debug flag which switches to event-driven for extra speed
eqs_stdp_ee = '''
w                             : 1
dpre/dt = -pre / tc_pre_ee    : 1 (clock-driven)
dpost/dt = -post / tc_post_ee : 1 (clock-driven)
'''

eqs_stdp_pre_ee = '''
ge_post += 3 * w * siemens
pre = 1
w = clip(w - nu_ee_pre * post - pre_w_decrease, 0, wmax_ee)
'''

eqs_stdp_post_ee_no_theta = '''
post = 1
w = clip(w + nu_ee_post * pre, 0, wmax_ee)
'''
eqs_stdp_post_ee_theta = eqs_stdp_post_ee_no_theta + '''
theta_post = clip(theta_post + theta_coef * nu_ee_post * pre, min_theta * mV, max_theta)
'''
