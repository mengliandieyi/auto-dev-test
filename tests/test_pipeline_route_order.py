"""流水线路由顺序回归：/jobs/prune 不得被 /jobs/{job_id} 吞掉。"""

import unittest


class TestPipelineRouteOrder(unittest.TestCase):
    def test_prune_route_before_job_id_param(self):
        from api.routers import pipeline as pl

        entries: list[tuple[str, str]] = []
        for route in pl.router.routes:
            path = getattr(route, "path", "") or ""
            methods = getattr(route, "methods", None) or set()
            for method in methods:
                if method in {"GET", "POST", "PUT", "DELETE"}:
                    entries.append((method, path))

        prune_idx = next(
            i for i, (m, p) in enumerate(entries) if m == "POST" and p.endswith("/jobs/prune")
        )
        job_detail_idx = next(
            i for i, (m, p) in enumerate(entries) if m == "GET" and p.endswith("/jobs/{job_id}")
        )
        self.assertLess(
            prune_idx,
            job_detail_idx,
            "POST /jobs/prune must be registered before GET /jobs/{job_id}",
        )


if __name__ == "__main__":
    unittest.main()
