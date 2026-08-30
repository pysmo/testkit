"""Pinned predicted-P arrivals for the ICCS/MCCC array fixture.

One entry per shipped ``iccs_events`` SAC file, keyed by ``(event label,
"NETWORK.STATION")``. These are the values ``fetch_iccs_events.py`` writes
into each SAC as ``t0`` (the initial pick) and uses to anchor the fetch
window (``t0 - 2 min`` to ``t0 + 3 min``).

Frozen, not recomputed. Originally from EarthScope's ``irisws-traveltime``
(retired 2026); the bundle was first cut against it. Regenerated straight
back out of the committed SAC ``t0`` headers by ``extract_predicted_p.py``
in this directory, so the table and the shipped files agree by
construction. ``tests/test_traveltime_windows.py`` checks these still
track pysmo's current tau-p solver, which now agrees to a few ms
everywhere except one branch-crossover cusp (see that test).
"""

PREDICTED_P: dict[tuple[str, str], str] = {
    # iraq
    ("iraq", "AK.BWN"): "2017-11-12T18:30:26.239500+00:00",
    ("iraq", "AK.CAPN"): "2017-11-12T18:30:42.641500+00:00",
    ("iraq", "AK.CAST"): "2017-11-12T18:30:28.599100+00:00",
    ("iraq", "AK.CCB"): "2017-11-12T18:30:24.473800+00:00",
    ("iraq", "AK.CHI"): "2017-11-12T18:31:03.154200+00:00",
    ("iraq", "AK.CHUM"): "2017-11-12T18:30:26.050200+00:00",
    ("iraq", "AK.EYAK"): "2017-11-12T18:30:46.520500+00:00",
    ("iraq", "AK.FYU"): "2017-11-12T18:30:15.182800+00:00",
    ("iraq", "AK.GRNC"): "2017-11-12T18:30:46.984800+00:00",
    ("iraq", "AK.HIN"): "2017-11-12T18:30:46.959100+00:00",
    ("iraq", "AK.JIS"): "2017-11-12T18:31:00.233700+00:00",
    ("iraq", "AK.KAI"): "2017-11-12T18:30:50.153800+00:00",
    ("iraq", "AK.KHIT"): "2017-11-12T18:30:47.986700+00:00",
    ("iraq", "AK.KIAG"): "2017-11-12T18:30:45.844100+00:00",
    ("iraq", "AK.KLU"): "2017-11-12T18:30:41.683100+00:00",
    ("iraq", "AK.KNK"): "2017-11-12T18:30:40.909000+00:00",
    ("iraq", "AK.MCK"): "2017-11-12T18:30:28.737500+00:00",
    ("iraq", "AK.NICH"): "2017-11-12T18:30:48.776700+00:00",
    ("iraq", "AK.PAX"): "2017-11-12T18:30:34.270300+00:00",
    ("iraq", "AK.PIN"): "2017-11-12T18:30:50.553300+00:00",
    ("iraq", "AK.PNL"): "2017-11-12T18:30:52.869500+00:00",
    ("iraq", "AK.SAMH"): "2017-11-12T18:30:50.262400+00:00",
    ("iraq", "AK.SKN"): "2017-11-12T18:30:36.311500+00:00",
    ("iraq", "AK.YAH"): "2017-11-12T18:30:48.864400+00:00",
    ("iraq", "AV.SPCP"): "2017-11-12T18:30:39.526300+00:00",
    ("iraq", "TA.POKR"): "2017-11-12T18:30:22.130400+00:00",
    ("iraq", "TA.TOLK"): "2017-11-12T18:30:01.923400+00:00",
    # komandorskiye_ostrova
    ("komandorskiye_ostrova", "AK.BWN"): "2017-07-17T23:39:17.859600+00:00",
    ("komandorskiye_ostrova", "AK.CAPN"): "2017-07-17T23:39:07.476500+00:00",
    ("komandorskiye_ostrova", "AK.CAST"): "2017-07-17T23:39:04.020600+00:00",
    ("komandorskiye_ostrova", "AK.CCB"): "2017-07-17T23:39:24.964500+00:00",
    ("komandorskiye_ostrova", "AK.CHUM"): "2017-07-17T23:39:03.526800+00:00",
    ("komandorskiye_ostrova", "AK.EYAK"): "2017-07-17T23:39:34.054000+00:00",
    ("komandorskiye_ostrova", "AK.FIRE"): "2017-07-17T23:39:12.244800+00:00",
    ("komandorskiye_ostrova", "AK.FYU"): "2017-07-17T23:39:36.351300+00:00",
    ("komandorskiye_ostrova", "AK.GRNC"): "2017-07-17T23:39:51.455000+00:00",
    ("komandorskiye_ostrova", "AK.JIS"): "2017-07-17T23:40:28.901000+00:00",
    ("komandorskiye_ostrova", "AK.KHIT"): "2017-07-17T23:39:45.270600+00:00",
    ("komandorskiye_ostrova", "AK.KIAG"): "2017-07-17T23:39:48.570700+00:00",
    ("komandorskiye_ostrova", "AK.KLU"): "2017-07-17T23:39:32.540200+00:00",
    ("komandorskiye_ostrova", "AK.KNK"): "2017-07-17T23:39:21.104000+00:00",
    ("komandorskiye_ostrova", "AK.MCK"): "2017-07-17T23:39:19.164000+00:00",
    ("komandorskiye_ostrova", "AK.NICH"): "2017-07-17T23:39:42.337200+00:00",
    ("komandorskiye_ostrova", "AK.PAX"): "2017-07-17T23:39:33.874900+00:00",
    ("komandorskiye_ostrova", "AK.PIN"): "2017-07-17T23:39:59.016400+00:00",
    ("komandorskiye_ostrova", "AK.PNL"): "2017-07-17T23:40:03.542900+00:00",
    ("komandorskiye_ostrova", "AK.SAMH"): "2017-07-17T23:39:56.627600+00:00",
    ("komandorskiye_ostrova", "AV.AKRB"): "2017-07-17T23:37:39.778900+00:00",
    ("komandorskiye_ostrova", "AV.MAPS"): "2017-07-17T23:37:33.854100+00:00",
    ("komandorskiye_ostrova", "AV.RDDF"): "2017-07-17T23:38:59.438300+00:00",
    ("komandorskiye_ostrova", "AV.SSBA"): "2017-07-17T23:37:53.023000+00:00",
    ("komandorskiye_ostrova", "TA.POKR"): "2017-07-17T23:39:26.792800+00:00",
    # solomon_islands
    ("solomon_islands", "AK.ATKA"): "2014-04-12T20:25:28.173300+00:00",
    ("solomon_islands", "AK.BAL"): "2014-04-12T20:27:09.723900+00:00",
    ("solomon_islands", "AK.BWN"): "2014-04-12T20:27:07.111800+00:00",
    ("solomon_islands", "AK.CCB"): "2014-04-12T20:27:11.146000+00:00",
    ("solomon_islands", "AK.EYAK"): "2014-04-12T20:27:01.438100+00:00",
    ("solomon_islands", "AK.FYU"): "2014-04-12T20:27:21.282300+00:00",
    ("solomon_islands", "AK.GRNC"): "2014-04-12T20:27:10.015800+00:00",
    ("solomon_islands", "AK.HIN"): "2014-04-12T20:26:59.437800+00:00",
    ("solomon_islands", "AK.JIS"): "2014-04-12T20:27:19.416500+00:00",
    ("solomon_islands", "AK.KIAG"): "2014-04-12T20:27:09.361900+00:00",
    ("solomon_islands", "AK.KNK"): "2014-04-12T20:26:59.092900+00:00",
    ("solomon_islands", "AK.MCK"): "2014-04-12T20:27:06.201100+00:00",
    ("solomon_islands", "AK.PAX"): "2014-04-12T20:27:09.725900+00:00",
    ("solomon_islands", "AK.PNL"): "2014-04-12T20:27:11.900400+00:00",
    ("solomon_islands", "TA.POKR"): "2014-04-12T20:27:13.293900+00:00",
    ("solomon_islands", "TA.TOLK"): "2014-04-12T20:27:21.781400+00:00",
}
