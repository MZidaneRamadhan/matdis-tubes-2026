from algorithms.maxflow import Dinic, FordFulkerson, PushRelabel
from algorithms.registry import AlgorithmRegistry

AlgorithmRegistry.register("dinic", Dinic)
AlgorithmRegistry.register("ford_fulkerson", FordFulkerson)
AlgorithmRegistry.register("push_relabel", PushRelabel)
AlgorithmRegistry.register_alias("maxflow", "dinic")

__all__ = ["AlgorithmRegistry", "Dinic", "FordFulkerson", "PushRelabel"]
