## This file is part of Jax Geometry
#
# Copyright (C) 2021, Stefan Sommer (sommer@di.ku.dk)
# https://bitbucket.org/stefansommer/jaxgeometry
#
# Jax Geometry is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Jax Geometry is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Jax Geometry. If not, see <http://www.gnu.org/licenses/>.
#

#%% Sources

#%% Modules

from jaxgeometry.setup import *
from .riemannian import Manifold

#%% Euclidean Geometry (R^n)

class nHyperbolicSpace(Manifold):
    """ Hyperbolic Space """
    
    def __str__(self)->str:
        
        return f"{self.dim}-dimensioanl Hyperbolic Space with curvate {self.K} embedded into R^{self.dim+1}"

    def __init__(self,N:int=3, inner_product:str='Lorentzian', K:float=-1.)->None:
        riemannian.Manifold.__init__(self)
        self.dim = N
        self.K = K

        self.do_chart_update = lambda x: False
        self.update_coords = lambda coords,_: coords

        ##### Metric:
            
        metric = jnp.eye(self.dim)
        if inner_product == 'Lorentizian':
            metric = metric.at[0,0].set(-1)
        else:
            metric = metric.at[-1,-1].set(-1)
            
        self.g = lambda x: metric

        # action of matrix group on elements
        self.act = lambda g,x: jnp.tensordot(g,x,(1,0))
        
        self.dot = lambda x,v,w: jnp.tensordot(jnp.tensordot(M.g(x),w,(1,0)),v,(0,0))
        self.norm = lambda x,v: jnp.sqrt(self.dot(x,v,v))
        self.dist = lambda x,y: 1/jnp.sqrt(jnp.abs(self.K))*jnp.arccosh(self.K*self.dot(x[0],y[0]))
        self.Exp = lambda x,v,T=1.0: jnp.cosh(self.norm(x,v)*jnp.sqrt(jnp.abs(self.K)))+\
            v*jnp.sinh(self.norm(x,v)*jnp.sqrt(jnp.abs(self.K)))/(jnp.sqrt(jnp.abs(self.K))*self.norm(x,v))
        self.Log = lambda x,y: (y[0]-K*jnp.dot(x[0],y[0])*x[0])*jnp.arcosh(self.K*jnp.dot(x[0],y[0]))/ \
            jnp.sinh(jnp.arccosh(self.K*jnp.dot(x[0],y[0])))
        self.ParallelTransport = lambda x,y,v: v-self.K*self.dot(y[0],v)*(x[0]+y[0])/(1+self.K*self.dot(x[0],y[0]))
        
        return
    
    def update_vector(self, coords:Array, new_coords:Array, new_chart:Array, v:Array)->Array:
        
        return v














