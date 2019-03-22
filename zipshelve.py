# Code modified from on: 
# https://gitlab.cern.ch/lhcb/Analysis/blob/cc7f3b47bba84adab101ffa3be44480fff786ee4/Analysis/Ostap/python/Ostap/ZipShelve.py
# Above code is Python2, tenatively modified to suit Python3
# =============================================================================
""" This is zip-version of shelve database.

Keeping the same interface and functionality as shelve data base,
ZipShelf allows much more compact file size through the on-flight
compression of the content

However is contains several new features:

 - Optionally it is possible to perform the compression
   of the whole data base, that can be rathe useful fo data base
   with large amount of keys
"""
# =============================================================================
__author__ = "Vanya BELYAEV Ivan.Belyaev@itep.ru"
__date__ = "2010-04-30"
__version__ = "$Revision$"
# =============================================================================

__all__ = ('ZipShelf', 'open', 'tmpdb')

try:
    from cPickle import Pickler, Unpickler, HIGHEST_PROTOCOL
except ImportError:
    from pickle import Pickler, Unpickler, HIGHEST_PROTOCOL

# ==============================================================================
import os
import zlib  # use zlib to compress DB-content
import shelve
import shutil
from io import BytesIO
import logging as logger


# =============================================================================


class ZipShelf(shelve.Shelf):
    """
    Zipped-version of ``shelve''-database     
    """

    def __init__(self, filename,  mode='c', protocol=HIGHEST_PROTOCOL, compress=zlib.Z_BEST_COMPRESSION,
                 writeback=False, silent=False):

        # expand the actual file name 
        filename = os.path.expandvars(filename)
        filename = os.path.expanduser(filename)
        filename = os.path.expandvars(filename)
        filename = os.path.expandvars(filename)

        self.__gzip = False
        self.__filename = filename
        self.__remove = False
        self.__silent = silent
        self.__opened = False

        if not self.__silent:
            logger.info('Open DB: %s' % filename)

        if filename.rfind('.gz') + 3 == len(filename):

            if os.path.exists(filename) and 'r' == mode:
                # gunzip into temporary location
                filename_ = self._gunzip(filename)
                if not os.path.exists(filename_):
                    raise TypeError("Unable to gunzip properly: %s" % filename)
                if not self.__silent:
                    size1 = os.path.getsize(filename)
                    size2 = os.path.getsize(filename_)
                    logger.info("GZIP uncompression %s: %.1f%%" % (filename, (size2 * 100.0) / size1))
                filename = filename_
                self.__filename = filename_
                self.__remove = True
            elif os.path.exists(filename) and 'r' != mode:
                # unzip in place
                filename_ = filename[:-3]
                # remove existing file (if needed) 
                if os.path.exists(filename_): os.remove(filename_)
                size1 = os.path.getsize(filename)
                # gunzip in place 
                self.__in_place_gunzip(filename)
                if not os.path.exists(filename_):
                    raise TypeError("Unable to gunzip properly: %s" % filename)
                if not self.__silent:
                    size2 = os.path.getsize(filename_)
                    logger.info("GZIP uncompression %s: %.1f%%" % (filename, (size2 * 100.0) / size1))
                filename = filename_
                self.__gzip = True
                self.__filename = filename_
                self.__remove = False
            else:
                filename = filename[:-3]
                self.__gzip = True
                self.__filename = filename

        import dbm
        shelve.Shelf.__init__(self, dbm.open(self.__filename, mode), protocol, writeback)
        self.compress_level = compress
        self.__opened = True

    def filename(self):
        return self.__filename

    # destructor
    def __del__(self):
        """
        Destructor 
        """
        if self.__opened:
            self.close()

    # list the available keys
    def __dir(self, pattern=''):
        """
        List the available keys (patterns included). Pattern matching is performed according to
        fnmatch/glob/shell rules [it is not regex!]
        """
        keys_ = self.keys()
        keys_.sort()
        if pattern:
            import fnmatch
            _keys = [k for k in keys_ if fnmatch.fnmatchcase(k, pattern)]
            keys_ = _keys

        for key in keys_:
            print(key)

    # list the available keys - alias
    def ls(self, pattern=''):
        """
        List the available keys (patterns included). Pattern matching is performed accoriding to
        fnmatch/glob/shell rules [it is not regex!]
        """
        return self.__dir(pattern)

    # close and gzip (if needed)
    def close(self):
        """
        Close the file (and gzip it if required) 
        """
        if not self.__opened:
            return

        shelve.Shelf.close(self)
        self.__opened = False

        if self.__remove and os.path.exists(self.__filename):
            if not self.__silent:
                logger.info('REMOVE: ', self.__filename)
            os.remove(self.__filename)

        if self.__gzip and os.path.exists(self.__filename):
            # get the initial size 
            size1 = os.path.getsize(self.__filename)
            # gzip the file
            self.__in_place_gzip(self.__filename)
            
            if not os.path.exists(self.__filename + '.gz'):
                logger.warning('Unable to compress the file %s ' % self.__filename)
            size2 = os.path.getsize(self.__filename + '.gz')
            if not self.__silent:
                logger.info('GZIP compression %s: %.1f%%' % (self.__filename, (size2 * 100.0) / size1))

    # gzip the file (``in-place'')
    def __in_place_gzip(self, filein):
        """
        Gzip the file ``in-place''
        
        It is better to use here ``os.system'' or ``popen''-family,
        but it does not work properly for multiprocessing environemnt
        
        """
        if os.path.exists(filein + '.gz'):
            os.remove(filein + '.gz')
        
        # gzip the file 
        fileout = self._gzip(filein)
         
        if os.path.exists(fileout):
            # rename the temporary file 
            shutil.move(fileout, filein + '.gz')
            
            import time
            time.sleep(3)
            
            # remove the original
            os.remove(filein)

    # gunzip the file (``in-place'')
    def __in_place_gunzip(self, filein):
        """
        Gunzip the file ``in-place''
        
        It is better to use here ``os.system'' or ``popen''-family,
        but unfortunately it does not work properly for multithreaded environemnt
        
        """
        filename = filein[:-3]
        if os.path.exists(filename): os.remove(filename)

        # gunzip the file 
        fileout = self._gunzip(filein)
                
        if os.path.exists(fileout):
            # rename the temporary file 
            shutil.move(fileout, filename)
            
            import time
            time.sleep(3)
            
            # remove the original
            os.remove(filein)

    # gzip the file into temporary location, keep original
    def _gzip(self, filein):
        """
        Gzip the file into temporary location, keep original
        """
        if not os.path.exists(filein):
            raise NameError("GZIP: non existing file: " + filein)

        import tempfile, gzip

        fin = file(filein, 'r')
        fd, fileout = tempfile.mkstemp(prefix='tmp_', suffix='_zdb.gz')
        fout = gzip.open(fileout, 'w')

        try:
            for all in fin:
                fout.write(all)
        finally:
            fout.close()
            fin.close()
            import time
            time.sleep(3)
        return fileout

    # gunzip the file into temporary location, keep original
    def _gunzip(self, filein):
        """
        Gunzip the file into temporary location, keep original
        """
        if not os.path.exists(filein):
            raise NameError("GUNZIP: non existing file: " + filein)

        import gzip, tempfile

        fin = gzip.open(filein, 'r')
        fd, fileout = tempfile.mkstemp(prefix='tmp_', suffix='_zdb')
        fout = file(fileout, 'w')

        try:
            for all in fin:
                fout.write(all)
        finally:
            fout.close()
            fin.close()
            import time
            time.sleep(3)
        return fileout

    # some context manager functionality
    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


# =============================================================================
# ``get-and-uncompress-item'' from dbase
def _zip_getitem(self, key):
    """
    ``get-and-uncompress-item'' from dbase 
    """
    try:
        value = self.cache[key]
    except KeyError:
        f = BytesIO(zlib.decompress(self.dict[key]))
        value = Unpickler(f).load()
        if self.writeback:
            self.cache[key] = value
    return value


# =============================================================================
# ``set-and-compress-item'' to dbase
def _zip_setitem(self, key, value):
    """
    ``set-and-compress-item'' to dbase 
    """
    if self.writeback:
        self.cache[key] = value
    f = BytesIO()
    p = Pickler(f, self._protocol)
    p.dump(value)
    self.dict[key] = zlib.compress(f.getvalue(), self.compresslevel)


ZipShelf.__getitem__ = _zip_getitem
ZipShelf.__setitem__ = _zip_setitem


# =============================================================================
# helper finction to access ZipShelve data base

def open(filename, mode='c', protocol=HIGHEST_PROTOCOL, compress_level=zlib.Z_BEST_COMPRESSION,
         writeback=False, silent=True):
    """
    Open a persistent dictionary for reading and writing.
    
    The filename parameter is the base filename for the underlying
    database.  As a side-effect, an extension may be added to the
    filename and more than one file may be created.  The optional flag
    parameter has the same interpretation as the flag parameter of
    anydbm.open(). The optional protocol parameter specifies the
    version of the pickle protocol (0, 1, or 2).
    
    See the module's __doc__ string for an overview of the interface.
    """

    return ZipShelf(filename, mode, protocol, compress_level, writeback, silent)

# =============================================================================
# TEMPORARY Zipped-version of ``shelve''-database


class TmpZipShelf(ZipShelf):
    """
    TEMPORARY Zipped-version of ``shelve''-database     
    """

    def __init__(self, protocol=HIGHEST_PROTOCOL, compress=zlib.Z_BEST_COMPRESSION, silent=False):

        # create temporary file name
        import tempfile
        filename = tempfile.mktemp(suffix='.zdb')

        ZipShelf.__init__(self, filename, 'n', protocol, compress, False, silent)

        # close and delete the file

    def close(self):
        # close the shelve file
        fname = self.filename()
        ZipShelf.close(self)

        # delete the file
        if os.path.exists(fname):
            try:
                os.unlink(fname)
            except:
                pass


# =============================================================================
# helper finction to open TEMPORARY ZipShelve data base


def tmpdb(protocol=HIGHEST_PROTOCOL, compress_level=zlib.Z_BEST_COMPRESSION, silent=True):
    """
    Open a TEMPORARY persistent dictionary for reading and writing.
    
    The optional protocol parameter specifies the
    version of the pickle protocol (0, 1, or 2).
    
    See the module's __doc__ string for an overview of the interface.
    """
    return TmpZipShelf(protocol,compress_level, silent)


# =============================================================================
if '__main__' == __name__:
    logger.info(__file__ + '\n')
    logger.info(80 * '*')
    logger.info(__doc__)
    logger.info(80 * '*')
    logger.info(' Author  : %s' % __author__)
    logger.info(' Version : %s' % __version__)
    logger.info(' Date    : %s' % __date__)
    logger.info(' Symbols : %s' % list(__all__))
    logger.info(80 * '*')

# =============================================================================
# The END 
# =============================================================================
