#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Sep  4 17:38:39 2023

@author: frederik
"""

#%% Sources

#%% Modules

from jaxgeometry.setup import *

#%% Parallel Transport

def initialize(M:object)->None:
    """ Riemannian parallel transport """

    def ode_parallel_transport(c:tuple[ndarray, ndarray, ndarray],
                               y:tuple[ndarray, ndarray, ndarray]
                               )->ndarray:
        t,xv,prevchart = c
        x,chart,dx = y
        prevx = xv[0]
        v = xv[1]

        if M.do_chart_update is not None:
            dx = jnp.where(jnp.sum(jnp.square(chart-prevchart)) <= 1e-5,
                    dx,
                    M.update_vector((x,chart),prevx,prevchart,dx)
                )
        dv = -jnp.einsum('ikl,k,l->i',M.Gamma_g((x,chart)),dx,v)
        
        return jnp.stack((jnp.zeros_like(x),dv))
    
    def chart_update_parallel_transport(xv:ndarray,prevchart:ndarray,
                                        y:tuple[ndarray, ndarray, ndarray]
                                        )->tuple[ndarray, ndarray]:
        x,chart,dx = y
        if M.do_chart_update is None:
            return (xv,chart)

        prevx = xv[0]
        v = xv[1]
        return (jnp.where(jnp.sum(jnp.square(chart-prevchart)) <= 1e-5,
                                       jnp.stack((x,v)),
                                       jnp.stack((x,M.update_vector((prevx,prevchart),x,chart,v)))),
                chart)

    parallel_transport = lambda v,dts,xs,charts,dxs: integrate(ode_parallel_transport,chart_update_parallel_transport,jnp.stack((xs[0],v)),charts[0],dts,xs,charts,dxs)
    M.parallel_transport = jit(lambda v,dts,xs,charts,dxs: parallel_transport(v,dts,xs,charts,dxs)[1][:,1])