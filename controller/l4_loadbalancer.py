from controller.l4_loadbalancing_ecmp import ECMPMixin
from controller.l3_router_lazy        import Router

# TODO somehow encode this stuff into topology if possible
# POOLS = {
#     '10.0.0.1:8000': ['h1:8000', 'h2:8000', 'h3:8000'],
#     '10.0.0.1:9000': ['h1:9000', 'h2:9000'],
# }
POOLS = {
    '10.0.0.1:8000': ['h1:8000'],
}

class LoadBalancer(ECMPMixin, Router):
    def init(self):
        Router.init(self)
        ECMPMixin.init_pools(self, POOLS)


if __name__ == "__main__":
    import sys
    sw_name = sys.argv[1]
    controller = LoadBalancer(sw_name).run_digest_loop()
