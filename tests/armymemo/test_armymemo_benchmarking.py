from armymemo.benchmarking import benchmark_renderers


def test_benchmark_renderers_reports_typst_for_basic_example():
    report = benchmark_renderers(["resources/examples/basic_mfr.Amd"], iterations=1)

    assert report.iterations == 1
    assert len(report.cases) == 1

    case = report.cases[0]
    engines = {engine.engine: engine for engine in case.engines}

    assert set(engines) == {"typst"}
    assert engines["typst"].parse_seconds >= 0
    assert engines["typst"].error is None
