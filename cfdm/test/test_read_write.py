import atexit
import datetime
import os
import platform
import subprocess
import tempfile
import unittest

import numpy

import faulthandler

faulthandler.enable()  # to debug seg faults and timeouts

import cfdm

warnings = False

# Set up temporary files
n_tmpfiles = 6
tmpfiles = [
    tempfile.mkstemp("_test_read_write.nc", dir=os.getcwd())[1]
    for i in range(n_tmpfiles)
]
(
    tmpfile,
    tmpfileh,
    tmpfileh2,
    tmpfilec,
    tmpfile0,
    tmpfile1,
) = tmpfiles


def _remove_tmpfiles():
    """Remove temporary files created during tests."""
    for f in tmpfiles:
        try:
            os.remove(f)
        except OSError:
            pass


atexit.register(_remove_tmpfiles)


class read_writeTest(unittest.TestCase):
    """TODO DOCS."""

    def setUp(self):
        """TODO DOCS."""
        # Disable log messages to silence expected warnings
        cfdm.LOG_LEVEL("DISABLE")
        # Note: to enable all messages for given methods, lines or
        # calls (those without a 'verbose' option to do the same)
        # e.g. to debug them, wrap them (for methods, start-to-end
        # internally) as follows: cfdm.LOG_LEVEL('DEBUG')
        #
        # < ... test code ... >
        # cfdm.log_level('DISABLE')
        self.filename = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "test_file.nc"
        )

        self.string_filename = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "string_char.nc"
        )

    def test_write_filename(self):
        """TODO DOCS."""
        f = cfdm.example_field(0)
        a = f.data.array

        cfdm.write(f, tmpfile)
        g = cfdm.read(tmpfile)

        with self.assertRaises(Exception):
            cfdm.write(g, tmpfile)

        self.assertTrue((a == g[0].data.array).all())

    def test_read_field(self):
        """TODO DOCS."""
        # Test field keyword of cfdm.read
        filename = self.filename

        f = cfdm.read(filename)
        self.assertEqual(len(f), 1, "\n" + str(f))

        f = cfdm.read(
            filename, extra=["dimension_coordinate"], warnings=warnings
        )
        self.assertEqual(len(f), 4, "\n" + str(f))

        f = cfdm.read(
            filename, extra=["auxiliary_coordinate"], warnings=warnings
        )
        self.assertEqual(len(f), 4, "\n" + str(f))

        f = cfdm.read(filename, extra="cell_measure")
        self.assertEqual(len(f), 2, "\n" + str(f))

        f = cfdm.read(filename, extra=["field_ancillary"])
        self.assertEqual(len(f), 4, "\n" + str(f))

        f = cfdm.read(filename, extra="domain_ancillary", warnings=warnings)
        self.assertEqual(len(f), 4, "\n" + str(f))

        f = cfdm.read(
            filename,
            extra=["field_ancillary", "auxiliary_coordinate"],
            warnings=warnings,
        )
        self.assertEqual(len(f), 7, "\n" + str(f))

        self.assertEqual(
            len(
                cfdm.read(
                    filename,
                    extra=["domain_ancillary", "auxiliary_coordinate"],
                    warnings=warnings,
                )
            ),
            7,
        )
        self.assertEqual(
            len(
                cfdm.read(
                    filename,
                    extra=[
                        "domain_ancillary",
                        "cell_measure",
                        "auxiliary_coordinate",
                    ],
                    warnings=warnings,
                )
            ),
            8,
        )

        f = cfdm.read(
            filename,
            extra=(
                "field_ancillary",
                "dimension_coordinate",
                "cell_measure",
                "auxiliary_coordinate",
                "domain_ancillary",
            ),
            warnings=warnings,
        )
        self.assertEqual(len(f), 14, "\n" + str(f))

    def test_read_write_format(self):
        """TODO DOCS."""
        f = cfdm.read(self.filename)[0]
        for fmt in (
            "NETCDF3_CLASSIC",
            "NETCDF3_64BIT",
            "NETCDF3_64BIT_OFFSET",
            "NETCDF3_64BIT_DATA",
            "NETCDF4",
            "NETCDF4_CLASSIC",
        ):
            cfdm.write(f, tmpfile, fmt=fmt)
            g = cfdm.read(tmpfile)
            self.assertEqual(len(g), 1)
            g = g[0]
            self.assertTrue(
                f.equals(g, verbose=3), f"Bad read/write of format: {fmt}"
            )

    def test_read_write_netCDF4_compress_shuffle(self):
        """TODO DOCS."""
        f = cfdm.read(self.filename)[0]
        for fmt in ("NETCDF4", "NETCDF4_CLASSIC"):
            for shuffle in (True,):
                for compress in (4,):  # range(10):
                    cfdm.write(
                        f, tmpfile, fmt=fmt, compress=compress, shuffle=shuffle
                    )
                    g = cfdm.read(tmpfile)[0]
                    self.assertTrue(
                        f.equals(g, verbose=3),
                        "Bad read/write with lossless compression: "
                        f"{fmt}, {compress}, {shuffle}",
                    )

    def test_read_write_missing_data(self):
        """TODO DOCS."""
        f = cfdm.read(self.filename)[0]
        for fmt in (
            "NETCDF3_CLASSIC",
            "NETCDF3_64BIT",
            "NETCDF3_64BIT_OFFSET",
            "NETCDF3_64BIT_DATA",
            "NETCDF4",
            "NETCDF4_CLASSIC",
        ):
            cfdm.write(f, tmpfile, fmt=fmt)
            g = cfdm.read(tmpfile)[0]
            self.assertTrue(
                f.equals(g, verbose=3), f"Bad read/write of format: {fmt}"
            )

    def test_read_mask(self):
        """TODO DOCS."""
        f = cfdm.example_field(0)

        N = f.size

        f.data[1, 1] = cfdm.masked
        f.data[2, 2] = cfdm.masked

        f.del_property("_FillValue", None)
        f.del_property("missing_value", None)

        cfdm.write(f, tmpfile)

        g = cfdm.read(tmpfile)[0]
        self.assertEqual(numpy.ma.count(g.data.array), N - 2)

        g = cfdm.read(tmpfile, mask=False)[0]
        self.assertEqual(numpy.ma.count(g.data.array), N)

        g.apply_masking(inplace=True)
        self.assertEqual(numpy.ma.count(g.data.array), N - 2)

        f.set_property("_FillValue", 999)
        f.set_property("missing_value", -111)
        cfdm.write(f, tmpfile)

        g = cfdm.read(tmpfile)[0]
        self.assertEqual(numpy.ma.count(g.data.array), N - 2)

        g = cfdm.read(tmpfile, mask=False)[0]
        self.assertEqual(numpy.ma.count(g.data.array), N)

        g.apply_masking(inplace=True)
        self.assertEqual(numpy.ma.count(g.data.array), N - 2)

    def test_write_datatype(self):
        """TODO DOCS."""
        f = cfdm.read(self.filename)[0]
        self.assertEqual(f.data.dtype, numpy.dtype(float))

        f.set_property("_FillValue", numpy.float64(-999.0))
        f.set_property("missing_value", numpy.float64(-999.0))

        cfdm.write(
            f,
            tmpfile,
            fmt="NETCDF4",
            datatype={numpy.dtype(float): numpy.dtype("float32")},
        )
        g = cfdm.read(tmpfile)[0]
        self.assertEqual(
            g.data.dtype,
            numpy.dtype("float32"),
            "datatype read in is " + str(g.data.dtype),
        )

    def test_read_write_unlimited(self):
        """TODO DOCS."""
        for fmt in (
            "NETCDF4",
            "NETCDF4_CLASSIC",
            "NETCDF3_CLASSIC",
            "NETCDF3_64BIT",
            "NETCDF3_64BIT_OFFSET",
            "NETCDF3_64BIT_DATA",
        ):
            f = cfdm.read(self.filename)[0]
            domain_axes = f.domain_axes()

            domain_axes["domainaxis0"].nc_set_unlimited(True)
            cfdm.write(f, tmpfile, fmt=fmt)

            f = cfdm.read(tmpfile)[0]
            domain_axes = f.domain_axes()
            self.assertTrue(domain_axes["domainaxis0"].nc_is_unlimited())

        fmt = "NETCDF4"
        f = cfdm.read(self.filename)[0]

        domain_axes = f.domain_axes()

        domain_axes["domainaxis0"].nc_set_unlimited(True)
        domain_axes["domainaxis2"].nc_set_unlimited(True)
        cfdm.write(f, tmpfile, fmt=fmt)

        f = cfdm.read(tmpfile)[0]
        domain_axes = f.domain_axes()
        self.assertTrue(domain_axes["domainaxis0"].nc_is_unlimited())
        self.assertTrue(domain_axes["domainaxis2"].nc_is_unlimited())

    def test_read_CDL(self):
        """TODO DOCS."""
        subprocess.run(
            " ".join(["ncdump", self.filename, ">", tmpfile]),
            shell=True,
            check=True,
        )
        subprocess.run(
            " ".join(["ncdump", "-h", self.filename, ">", tmpfileh]),
            shell=True,
            check=True,
        )
        subprocess.run(
            " ".join(["ncdump", "-c", self.filename, ">", tmpfilec]),
            shell=True,
            check=True,
        )

        f0 = cfdm.read(self.filename)[0]
        f = cfdm.read(tmpfile)[0]
        cfdm.read(tmpfileh)[0]
        c = cfdm.read(tmpfilec)[0]

        self.assertTrue(f0.equals(f, verbose=3))

        self.assertTrue(
            f.construct("grid_latitude").equals(
                c.construct("grid_latitude"), verbose=3
            )
        )
        self.assertTrue(
            f0.construct("grid_latitude").equals(
                c.construct("grid_latitude"), verbose=3
            )
        )

        with self.assertRaises(OSError):
            cfdm.read("test_read_write.py")

        # TODO: make portable instead of skipping on Mac OS (see Issue #25):
        #       '-i' aspect solved, but the regex patterns need amending too.
        if platform.system() != "Darwin":  # False for Mac OS(X) only
            for regex in [
                r'"1 i\ \ "',
                r'"1 i\// comment"',
                r'"1 i\ // comment"',
                r'"1 i\ \t// comment"',
            ]:
                # Note that really we just want to do an in-place sed
                # ('sed -i') but because of subtle differences between the
                # GNU (Linux OS) and BSD (some Mac OS) command variants a
                # safe portable one-liner may not be possible. This will
                # do, overwriting the intermediate file. The '-E' to mark
                # as an extended regex is also for portability.
                subprocess.run(
                    " ".join(
                        [
                            "sed",
                            "-E",
                            "-e",
                            regex,
                            tmpfileh,
                            ">" + tmpfileh2,
                            "&&",
                            "mv",
                            tmpfileh2,
                            tmpfileh,
                        ]
                    ),
                    shell=True,
                    check=True,
                )

                cfdm.read(tmpfileh)[0]

    #        subprocess.run(' '.join(['head', tmpfileh]),  shell=True, check=True)

    def test_read_write_string(self):
        """TODO DOCS."""
        f = cfdm.read(self.string_filename)

        n = int(len(f) / 2)

        for i in range(0, n):
            j = i + n
            self.assertTrue(
                f[i].data.equals(f[j].data, verbose=3),
                "{!r} {!r}".format(f[i], f[j]),
            )
            self.assertTrue(
                f[j].data.equals(f[i].data, verbose=3),
                "{!r} {!r}".format(f[j], f[i]),
            )

        f0 = cfdm.read(self.string_filename)
        for string0 in (True, False):
            for fmt0 in ("NETCDF4", "NETCDF3_CLASSIC"):
                cfdm.write(f0, tmpfile0, fmt=fmt0, string=string0)

                for string1 in (True, False):
                    for fmt1 in ("NETCDF4", "NETCDF3_CLASSIC"):
                        cfdm.write(f0, tmpfile1, fmt=fmt1, string=string1)

                        for i, j in zip(
                            cfdm.read(tmpfile1), cfdm.read(tmpfile0)
                        ):
                            self.assertTrue(i.equals(j, verbose=3))

    def test_read_write_Conventions(self):
        """TODO DOCS."""
        f = cfdm.read(self.filename)[0]

        version = "CF-" + cfdm.CF()
        other = "ACDD-1.3"

        for Conventions in (other,):
            cfdm.write(f, tmpfile0, Conventions=Conventions)
            g = cfdm.read(tmpfile0)[0]
            self.assertEqual(
                g.get_property("Conventions"),
                " ".join([version, other]),
                "{!r}, {!r}".format(
                    g.get_property("Conventions"), Conventions
                ),
            )

        for Conventions in (
            version,
            "",
            " ",
            ",",
            ", ",
        ):
            Conventions = version
            cfdm.write(f, tmpfile0, Conventions=Conventions)
            g = cfdm.read(tmpfile0)[0]
            self.assertEqual(
                g.get_property("Conventions"),
                version,
                "{!r}, {!r}".format(
                    g.get_property("Conventions"), Conventions
                ),
            )

        for Conventions in (
            [version],
            [version, other],
        ):
            cfdm.write(f, tmpfile0, Conventions=Conventions)
            g = cfdm.read(tmpfile0)[0]
            self.assertEqual(
                g.get_property("Conventions"),
                " ".join(Conventions),
                "{!r}, {!r}".format(
                    g.get_property("Conventions"), Conventions
                ),
            )

        for Conventions in ([other, version],):
            cfdm.write(f, tmpfile0, Conventions=Conventions)
            g = cfdm.read(tmpfile0)[0]
            self.assertEqual(
                g.get_property("Conventions"),
                " ".join([version, other]),
                "{!r}, {!r}".format(
                    g.get_property("Conventions"), Conventions
                ),
            )

    def test_read_write_multiple_geometries(self):
        """TODO DOCS."""
        a = []
        for filename in (
            "geometry_1.nc",
            "geometry_2.nc",
            "geometry_3.nc",
            "geometry_4.nc",
            "geometry_interior_ring_2.nc",
            "geometry_interior_ring.nc",
        ):
            a.extend(cfdm.read(filename))

        for n, f in enumerate(a):
            f.set_property("test_id", str(n))

        cfdm.write(a, tmpfile, verbose=1)

        f = cfdm.read(tmpfile, verbose=1)

        self.assertEqual(len(a), len(f))

        for x in a:
            for n, y in enumerate(f[:]):
                if x.equals(y):
                    f.pop(n)
                    break

        self.assertFalse(f)

    def test_write_coordinates(self):
        """TODO DOCS."""
        f = cfdm.example_field(0)

        cfdm.write(f, tmpfile, coordinates=True)
        g = cfdm.read(tmpfile)

        self.assertEqual(len(g), 1)
        self.assertTrue(g[0].equals(f))

    def test_write_scalar_domain_ancillary(self):
        """TODO DOCS."""
        f = cfdm.example_field(1)

        # Create scalar domain ancillary
        d = f.construct("ncvar%a")
        d.del_data()
        d.set_data(10)
        d.del_bounds()

        key = f.construct_key("ncvar%a")
        f.set_data_axes((), key=key)

        cfdm.write(f, tmpfile)


if __name__ == "__main__":
    print("Run date:", datetime.datetime.now())
    cfdm.environment()
    print("")
    unittest.main(verbosity=2)
