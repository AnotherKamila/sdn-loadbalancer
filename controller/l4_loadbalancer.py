from controller.base_controller_twisted import main
from controller.l4_loadbalancing_ecmp import EqualCostLoadBalancer
from controller.l3_router_lazy        import Router
from controller.settings              import load_pools

pools = load_pools('./pools.json')

class LoadBalancer(EqualCostLoadBalancer, Router):
    def init(self):
        return EqualCostLoadBalancer.init_pools(self, pools)


if __name__ == "__main__":
    main(LoadBalancer)
