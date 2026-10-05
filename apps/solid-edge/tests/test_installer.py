import io, sys, tarfile, tempfile, unittest, zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'runtime/scripts'))
from installer import discover, extract

class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
    def tearDown(self): self.temp.cleanup()
    def fixture(self):
        p = self.root/'outer folder'/'nested release'/'Solid Edge'
        p.mkdir(parents=True)
        for f in ['setup.exe','Setup.ini','Siemens Solid Edge 2026.msi','data1.cab','data2.cab','LicenseFile/SELicense.lic','ISSetupPrerequisites/dummy.txt']:
            x=p/f; x.parent.mkdir(parents=True,exist_ok=True); x.write_text('SYNTHETIC NONEXECUTABLE TEST DATA')
        return p
    def test_nested_spaces_zip_and_tar(self):
        p=self.fixture()
        self.assertEqual(discover(self.root),p/'setup.exe')
        z=self.root/'installer.zip'
        with zipfile.ZipFile(z,'w') as a:
            for f in p.rglob('*'):
                if f.is_file(): a.write(f,f.relative_to(self.root))
        setup=extract(z,self.root/'prepared zip')
        self.assertEqual(setup.name,'setup.exe')
        self.assertTrue((setup.parent/'data2.cab').is_file())
        t=self.root/'installer.tar.gz'
        with tarfile.open(t,'w:gz') as a: a.add(p,arcname='deep folder/Solid Edge')
        self.assertTrue(extract(t,self.root/'prepared tar').is_file())
    def test_missing_and_ambiguous(self):
        p=self.fixture(); (p/'Setup.ini').unlink()
        with self.assertRaises(ValueError): discover(self.root)
        (p/'Setup.ini').touch()
        import shutil
        shutil.copytree(p,self.root/'second')
        with self.assertRaises(ValueError): discover(self.root)
    def test_zip_traversal_and_windows_paths(self):
        for name in ['../escape','/absolute','C:/escape','..\\escape']:
            z=self.root/'bad.zip'
            with zipfile.ZipFile(z,'w') as a: a.writestr(name,'bad')
            with self.assertRaises(ValueError): extract(z,self.root/'out')
        self.assertEqual(list((self.root/'out').iterdir()),[])
    def test_tar_links_and_special_files(self):
        for kind in [tarfile.SYMTYPE,tarfile.LNKTYPE,tarfile.FIFOTYPE]:
            t=self.root/'bad.tar'
            with tarfile.open(t,'w') as a:
                m=tarfile.TarInfo('link'); m.type=kind;m.linkname='/etc/passwd';a.addfile(m)
            with self.assertRaises(ValueError): extract(t,self.root/'out')
    def test_zip_symlink_and_duplicate(self):
        z=self.root/'bad.zip'
        with zipfile.ZipFile(z,'w') as a:
            m=zipfile.ZipInfo('link');m.create_system=3;m.external_attr=0o120777<<16;a.writestr(m,'/etc/passwd')
        with self.assertRaises(ValueError): extract(z,self.root/'out')
        with zipfile.ZipFile(z,'w') as a:
            a.writestr('Setup.ini','a');a.writestr('setup.ini','b')
        with self.assertRaises(ValueError): extract(z,self.root/'out')
    def test_size_limit_and_invalid_archive(self):
        import installer
        z=self.root/'big.zip'
        with zipfile.ZipFile(z,'w') as a:a.writestr('file','12345')
        previous=installer.MAX_BYTES;installer.MAX_BYTES=4
        try:
            with self.assertRaises(ValueError):extract(z,self.root/'out')
        finally: installer.MAX_BYTES=previous
        z.write_text('broken')
        with self.assertRaises(tarfile.ReadError):extract(z,self.root/'out')
    def test_host_symlink(self):
        p=self.fixture();(p/'link').symlink_to('/etc/passwd')
        with self.assertRaises(ValueError): discover(self.root)
if __name__=='__main__': unittest.main()
