#  -*- Python -*- -*- coding: iso-8859-1 -*-
# :Progetto: Bice -- Scombinatore di file
# :Sorgente: $HeadURL: http://svn.bice.dyndns.org/progetti/wip/tools/cvsync/tests/scrambler.py $
# :Creato:   mar 20 apr 2004 16:21:34 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# :Modifica: $LastChangedDate: 2004-04-23 15:24:11 +0200 (ven, 23 apr 2004) $
# :Fatta da: $LastChangedBy: lele $
# 

class Scrambler:
    """Perform various perturbations to the files in a directory.
    """
    
    def __init__(self, dir, seed, delete_files=True):
        from random import Random
        
        self.seed = seed
        self.dir = dir
        self.greeking = '\n'.join(
            ["This was line number %d, as originally crafted by the tester."
             % line for line in range(10)])

        self.file_modders = [self.append_to_file,
                             self.append_to_file,
                             self.remove_from_file,
                             self.remove_from_file,
                             self.alter_file,
                             self.alter_file,
                             self.alter_file,
                             self.alter_file,
                             ]

        if delete_files:
            self.file_modders.append(self.delete_file)
            
        self.rand = Random(seed)
        
    def __call__(self, notify=None):
        from os import walk, chdir
        from os.path import join

        chdir(self.dir)
        mods = []
        for root, dirs, files in walk(self.dir):
            mods.extend(self.maybe_add_file_or_dir(root))
            if '.svn' in dirs: dirs.remove('.svn')
            if 'CVS' in dirs: dirs.remove('CVS')
            
            base = root[len(self.dir)+1:]

            for file in files:
                # Only do something 33% of the time
                if self.rand.randrange(3):
                    modder = self.rand.choice(self.file_modders)
                    res = modder(join(base, file))
                    mods.extend(res)

        if notify:
            for mod in mods:
                list = getattr(notify, mod[0])
                if mod[1] not in list:
                    list.append(mod[1])
   
    def __shrink_list(self, seq):
        if len(seq) < 6:
            return seq
        
        if type(seq) == type(''):
            wasseq = False
            seq = list(seq)
        else:
            wasseq = True
            
        # remove 5 random lines (ranges)
        for i in range(5):
            l = len(seq)
            if l<2:
                break
            j = self.rand.randrange(l - 1)
            k = self.rand.randrange(l - 1)
            if k>j:
                del seq[j:k]
            else:
                del seq[j]
                
        if wasseq:
            return seq
        else:
            return ''.join(seq)

    def __augment_list(self, seq):
        if type(seq) == type(''):
            wasseq = False
            seq = list(seq)
        else:
            wasseq = True
            
        # duplicate 5 random lines (ranges)
        for i in range(5):
            l = len(seq)
            if l<2:
                seq.append(seq[0])
            else:
                j = self.rand.randrange(l - 1)
                k = self.rand.randrange(l - 1)
                if k>j:
                    seq[j:j] = seq[k]
                else:
                    seq[k:k] = seq[j:j+k]
        if wasseq:
            return seq
        else:
            return ''.join(seq)

    def __edit_list(self, list):
        if len(list)<2:
            return list
        
        # edit 5 random lines (ranges)
        for i in range(5):
            l = len(list)
            j = self.rand.randrange(l - 1)
            k = self.rand.randrange(l - 1)
            if k>j:
                list[j] = self.__shrink_list(list[j])
            else:
                list[j] = self.__augment_list(list[j])
        return list
    
    def append_to_file(self, path):
        fh = open(path, "a")
        fh.write(self.greeking)
        fh.close()
        return ( ('modified', path), )

    def alter_file(self, path):
        lines = self.__augment_list(open(path, "r").readlines())
        lines = self.__shrink_list(lines)
        lines = self.__edit_list(lines)       
        open(path, "w").writelines(lines)
        return ( ('modified', path), )
        
    def remove_from_file(self, path):
        lines = self.__shrink_list(open(path, "r").readlines())
        open(path, "w").writelines(lines)
        return ( ('modified', path), )
        
    def delete_file(self, path):
        from os import remove, listdir
        from os.path import split
        from shutil import rmtree

        dir = split(path)[0]
        if not dir:
            dir = self.dir
        if len(listdir(dir)) == 1:
            rmtree(path)
            return ( ('removed_dirs', path), )
        else:
            remove(path)
            return ( ('removed', path), )

    def maybe_add_file_or_dir(self, dir):
        from os import write, close
        from os.path import join
        from tempfile import mkstemp, mkdtemp

        mods = []
        if self.rand.randrange(3) == 2:
            if self.rand.randrange(7) == 1:
                dir = mkdtemp(dir=dir, prefix='dir')
                mods.append( ('added_dirs', dir[len(self.dir)+1:]) )

            fd,name = mkstemp(dir=dir, text=True, prefix='file', suffix='.txt')
            write(fd, self.greeking)
            close(fd)

            mods.append( ('added', name[len(self.dir)+1:]) )
        return mods

