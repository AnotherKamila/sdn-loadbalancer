from controller.l4_loadbalancing_ecmp import ECMPMixin
from controller.l3_router_lazy        import Router
from controller.settings              import load_pools

pools = load_pools('./pools.json')

class LoadBalancer(ECMPMixin, Router):
    def init(self):
        Router.init(self)
        ECMPMixin.init_pools(self, pools)


if __name__ == "__main__":
    import sys
    sw_name = sys.argv[1]
    controller = LoadBalancer(sw_name).run_digest_loop()
