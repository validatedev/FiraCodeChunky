def test_masters_are_point_compatible(micro_masters):
    light, bold = micro_masters
    assert sorted(light.keys()) == sorted(bold.keys())
    for name in light.keys():  # noqa: SIM118
        lg, bg = light[name], bold[name]
        assert len(lg.contours) == len(bg.contours)
        for lc, bc in zip(lg.contours, bg.contours, strict=True):
            assert len(lc.points) == len(bc.points)


def test_known_values(micro_masters, micro_ds):
    light, bold = micro_masters
    assert light["I"].contours[0].points[0].x == 280
    assert bold["I"].contours[0].points[0].x == 240
    assert light.kerning[("I", "O")] == -8
    assert bold.kerning[("I", "O")] == -40
    assert [i.styleName for i in micro_ds.instances] == [
        "Light",
        "Regular",
        "Retina",
        "Medium",
        "SemiBold",
        "Bold",
    ]
