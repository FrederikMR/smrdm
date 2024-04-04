#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Sep 29 13:05:11 2023

@author: fmry
"""

#%% Sources

#%% Modules

#jax,
from jaxgeometry.setup import *

#%% VAE Loss Fun

#@jit
def vae_euclidean_loss(params:hk.Params, state_val:dict, rng_key:Array, x, vae_apply_fn,
                       training_type="All")->Array:
    
    @jit
    def gaussian_likelihood(x, mu_xz, log_sigma_xz):
        
        dim = mu_xz.shape[-1]
        diff = x-mu_xz
        sigma_xz = jnp.exp(log_sigma_xz)
        mu_term = jnp.sum(jnp.einsum('ij,ij->ij', diff**2, 1/(sigma_xz**2)), axis=-1)
        var_term = 2*dim*jnp.sum(log_sigma_xz, axis=-1)
        
        loss = -0.5*(mu_term+var_term)
        
        return jnp.mean(loss)
    
    @jit
    def kl_divergence(z, mu_zx, log_t_zx, mu_z, log_t_z):
        
        dim = mu_zx.shape[-1]
        diff = z-mu_zx
        log_t_zx = log_t_zx.squeeze()
        log_t_z = log_t_z.squeeze()
        t_zx = jnp.exp(log_t_zx)
        t_z = jnp.exp(log_t_z)
        dist = jnp.sum(jnp.einsum('ij,i->ij', diff**2, 1/(t_zx**2)), axis=-1)
        log_qzx = -0.5*(dim*log_t_zx+dist)
        
        diff = z-mu_z
        dist = jnp.sum(jnp.einsum('ij,i->ij', diff**2, 1/(t_z**2)), axis=-1)
        log_pz = -0.5*(dim*log_t_z+dist)
        
        return jnp.mean(log_qzx-log_pz)

    z, mu_xz, log_sigma_xz, mu_zx, log_t_zx, mu_z, log_t_z = vae_apply_fn(params, x, rng_key, state_val)

    if training_type == "Encoder":
        sigma_xz = lax.stop_gradient(log_sigma_xz)
        mu_z = lax.stop_gradient(mu_z)
        t_z = lax.stop_gradient(log_t_z)
    elif training_type == "Decoder":
        mu_xz = lax.stop_gradient(mu_xz)
        t_zx = lax.stop_gradient(log_t_zx)
        mu_zx = lax.stop_gradient(mu_zx)

    rec_loss = gaussian_likelihood(x, mu_xz, log_sigma_xz)
    kld = kl_divergence(z, mu_zx, log_t_zx, mu_z, log_t_z)
    elbo = kld-rec_loss
    
    return elbo, (rec_loss, kld)
#%% VAE Riemannian Fun

@jit
def vae_riemannian_loss(params:hk.Params, state_val:dict, rng_key:Array, x:Array, vae_apply_fn,
                        score_apply_fn, score_state, training_type="All"):
    
    @jit
    def gaussian_likelihood(params:hk.Params):
        
        _, mu_xz, sigma_xz, *_ = vae_apply_fn(params, x, rng_key, state_val)
        
        dim = mu_xz.shape[-1]
        mu_term = jnp.einsum('...i,...i->...', x-mu_xz, (x-mu_xz)/sigma_xz)
        var_term = dim*jnp.sum(jnp.log(sigma_xz), axis=-1)
        
        return -0.5*(mu_term+var_term)
    
    @jit
    def encoder_fun(params:hk.Params):
        
        z, *_ = vae_apply_fn(params, x, rng_key, state_val)

        return z
            
    z, mu_xz, log_sigma_xz, mu_zx, log_t_zx, mu_z, log_t_z = vae_apply_fn(params, x, rng_key, state_val)
    
    if training_type == "Encoder":
        sigma_xz = lax.stop_gradient(sigma_xz)
        mu_z = lax.stop_gradient(mu_z)
        t_z = lax.stop_gradient(t_z)
    elif training_type == "Decoder":
        mu_xz = lax.stop_gradient(mu_xz)
        t_zx = lax.stop_gradient(t_zx)
        mu_zx = lax.stop_gradient(mu_zx)
    
    z_grad = jacfwd(encoder_fun)(params)
    rec_grad = -grad(gaussian_likelihood)(params)
    
    s_logqzx = vmap(lambda mu,z,t: score_apply_fn(score_state.params, jnp.hstack((mu,z,t)), 
                              score_state.rng_key, score_state.state_val))(mu,z,t)
    s_logpz = vmap(lambda mu0,z,t0: score_apply_fn(score_state.params, jnp.hstack((mu0,z,t0)), 
                             rng_key, score_state.state_val))(mu0,z,t0)
    diff = s_logqzx-s_logpz

    if x.ndim == 1:
        kl_grad = {layer: {name: jnp.einsum('i,i...->...', diff, w) for name,w in val.items()} \
                   for layer,val in z_grad.items()}
    else:
        kl_grad = {layer: {name: jnp.mean(jnp.einsum('ki,ki...->k...', diff, w), axis=0) for name,w in val.items()} \
                   for layer,val in z_grad.items()}
    #z_grad.update((x, jnp.einsum('...i,...ij->...j')) for v,w in x for x, y in my_dict.items())
    #kl_grad = jnp.mean(jnp.einsum('...i,...ij->...j', s_logqzx-s_logpz, z_grad), axis=0)
    
    res = {layer: {name: kl_grad[layer][name]-rec_grad[layer][name] for name,w in val.items()} \
               for layer,val in z_grad.items()}

    return res