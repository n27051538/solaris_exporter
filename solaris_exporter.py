#!/usr/bin/python
"""
solaris_exporter.py
version v2022Feb05
    2020 Jan 31. Initial
    2020 Feb 04. Added UpTime in UpTimeCollector.
    2020 Feb 09. Added DiskErrorCollector, ZpoolCollector, FmadmCollector, SVCSCollector, FCinfoCollector
    2020 Dec 17. Added PrtdiagCollector, MetaStatCollector, MetaDBCollector
    2021 Jan 05. Added TextFileCollector, SVCSCollector now enabled for all zones (Thanks to Marcel Peter)
    2021 Mar 01. Fixed psutil version to 5.7.0 (something changed in the newer versions, have to time to look at)
    2022 Jan 24. Added support for Python 3.7. In testing.
    2022 Feb 04. Documentation update for support of Solaris 11.4.41. In testing.
    2022 Feb 05. Fixed support of Python 2.7 for Solaris 11.4.41
                 (https://github.com/n27051538/solaris_exporter/issues/7). In testing.

Written by Alexander Golikov for collecting SPARC Solaris metrics for Prometheus.

Tested on Solaris 11.3.25, 11.4.4, 10u11(limited) SPARC.
May be it also will work on x86 platform, but this is not tested.

This exporter provides info about:
  - Solaris Zones CPU Usage with processor sets info (PerZoneCpuCollector);
  - Solaris Zones Virtual Memory (SWAP) Resource Capping (PerZoneCapsCollector);
  - Common CPU stats (CpuTimeCollector);
  - Avg Load (CpuLoadCollector);
  - Disk IO (DiskIOCollector);
  - Disk Errors (DiskErrorCollector);
  - Disk Space (DiskSpaceCollector, requires 'file_dac_search' priv for solaris zones)
  - Memory Usage, swap-in, swap-out (MemCollector);
  - Network Interfaces (NetworkCollector);
  - Node time, uptime (CurTimeCollector, UpTimeCollector);
  - FC links Multipath (FCinfoCollector, /usr/sbin/mpathadm list lu)
  - System Services health via 'svcs -x' command (SVCSCollector);
  - Whole system health via 'fmadm faulty' (FmadmCollector), requires pfexec of '/usr/sbin/fmadm'.
  - Zpool devices health via 'zpool status' command (ZpoolCollector)
  - Solaris Volume Manager disk status (MetaStatCollector, MetaDBCollector).
  - Get info from text files *.prom in folder provided by text_file_path var (TextFileCollector).

Installation. To use this exporter you need python2.7 or python3.x and its modules prometheus_client, psutil.


    Solaris 10u11:
        # Setup proxy vars to have access to internet
            export http_proxy=http://proxy.example.com:3128
            export https_proxy=http://proxy.example.com:3128
        # Install pkgutil
            wget http://get.opencsw.org/now
            pkgadd -d ./now
        # Update repo list
            /opt/csw/bin/pkgutil -U
        # Install Python 2.7 or Python 3.3 (it works on both)
            # Python 2.7 (preferred)
                /opt/csw/bin/pkgutil -y -i python27
                /opt/csw/bin/pkgutil -y -i python27_dev
                /opt/csw/bin/pkgutil -y -i py_pip
                /usr/sbin/pkgchk -L CSWpy-pip               # list installed files if you need
            # or Python 3.3
                /opt/csw/bin/pkgutil -y -i python33
                /opt/csw/bin/pkgutil -y -i python33_dev
                # pip3 is not included in pkgutil, we need to install it by hands
                # download pip3.3 installer [https://bootstrap.pypa.io/pip/3.3/get-pip.py] and run it with python3.3
                /opt/csw/bin/python3.3 get-pip.py
        #Install gcc5core
            /opt/csw/bin/pkgutil -y -i gcc5core
        # Install Python module prometheus_client
            # Python 2.7
                /opt/csw/bin/pip2.7 install prometheus_client
            # or Python 3.3
                /opt/csw/bin/pip3.3 install prometheus_client
        # Install Python module psutil, it have to compile some libs, but we preinstalled all that needed
            ln -s /opt/csw/bin/gcc-5.5 /opt/csw/bin/gcc-5.2
            # Python 2.7
                # note that the latest version of psutil not supports Python2.7,
                # that is why version of psutil is fixed to '5.7.0'
                    /opt/csw/bin/pip2.7 install psutil==5.7.0
            # or Python 3.3
                /opt/csw/bin/pip3.3 install psutil
        # Run exporter, check http://ip:9100
            # Python 2.7
            export LANG=C
            /opt/csw/bin/python2.7 solaris_exporter.py
            # or Python 3.3
            export LANG=C
            /opt/csw/bin/python3.3 solaris_exporter.py


    Solaris 11.4.4(this way works with Python 2.7, it is included in this release):
        # Setup proxy vars to have access to internet
            export http_proxy=http://proxy.example.com:3128
            export https_proxy=http://proxy.example.com:3128
        # Install Python 2.7 module prometheus_client
            pip-2.7 install prometheus_client
        # Install Python 2.7 module psutil, it have to compile some libs
        # Also you could get psutil for Python 2.7 via 'pkg install library/python/psutil-27',
        # but it returns wrong Network statistics, tested from Solaris 11.4.4 repo.
        # The latest version of psutil not supports Python2.7, that is why version of psutil is fixed on '5.7.0'
            pkg install pkg:/developer/gcc/gcc-c-5
            ln -s /usr/bin/gcc /usr/bin/cc
            export CFLAGS=-m32
            pip-2.7 install psutil==5.7.0
            # if you have troubles with compilation, try to switch to gcc-c-9 and Python 3.7
        # Run exporter, check http://ip:9100
            export LANG=C
            python2.7 solaris_exporter.py


    Solaris 11.4.41(this way works with Python 3.7):
        # Setup proxy vars to have access to internet
            export http_proxy=http://proxy.example.com:3128
            export https_proxy=http://proxy.example.com:3128
        # Install Python 3.7 module prometheus_client
            pip-3.7 install prometheus_client
        # Install Python 3.7 module psutil
        # Also you could get psutil for Python 3.7 via 'pkg install library/python/psutil-37',
        # but its old version '5.6.7' not adapted for Sol11.4.41 changes, fails at 'swap -l' output, have network dev inaccuracy.
        # The best way is to install actual version of psutil (tested on '5.9.0')
            pkg install pkg:/developer/gcc/gcc-c-9
            ln -s /usr/bin/gcc /usr/bin/cc
            pip-3.7 install psutil==5.9.0
        # Run exporter, check http://ip:9100
            export LANG=C
            python3.7 solaris_exporter.py

"""
import time
import re
import subprocess
import threading
import socket
import psutil
from psutil import _psutil_sunos as cext
import os
from prometheus_client.core import REGISTRY, Counter, Gauge, GaugeMetricFamily, CounterMetricFamily, UntypedMetricFamily
from prometheus_client.parser import text_string_to_metric_families
from prometheus_client import start_http_server
from glob import glob
from collections import namedtuple

exporter_port = 9100
text_file_path = '/opt/solaris_exporter/'
dictionaries_refresh_interval_sec = 600
disk_operations_dictionary = {
    'reads': 'number of read operations',
    'writes': 'number of write operations',
    'nread': 'number of bytes read',
    'nwritten': 'number of bytes written',

    'wlentime': 'cumulative wait length time product',
    'rlentime': 'cumulative run length time product',

    'rtime': 'cumulative run service time',
    'wtime': 'cumulative wait pre-service time',

    'rcnt': 'count of elements in run state',
    'wcnt': 'count of elements in wait state',

    'crtime': 'creation time in seconds with nano',
    'snaptime': 'time of last data snapshot in seconds with nano',

    'rlastupdate': 'last time run queue changed in seconds with nano',
    'wlastupdate': 'last time wait queue changed in seconds with nano',
}
per_zone_cpu_counters_dictionary = {
    'cpu_nsec_kernel': 'per CPU microstate counter kernel time for zone, seconds',
    'cpu_nsec_user': 'per CPU microstate counter user time for zone, seconds',
    'readch': 'bytes read for zone',
    'writech': 'bytes wrote for zone',
    'sysread': 'read count for zone',
    'syswrite': 'write count for zone',
    'syscall': 'system calls for zone',
    'sysexec': 'execs for zone',
    'sysfork': 'forks for zone',
    'sysspawn': 'spawns for zone',
}


def run_shell_command(commandline, timeout):
    """
    Run OS command with timeout and status return. Also works in Python 2.7.
    Example:
    output, task_return_code, task_timeouted = run_shell_command('shell command text', timeout)
    """
    output = ""
    task_timeouted = False
    task_return_code = 100
    FNULL = open(os.devnull, 'w')
    try:
        task = subprocess.Popen(commandline.split(), shell=False, stdout=subprocess.PIPE, stderr=FNULL)
    except OSError:
        task_return_code = 101
        return "", task_return_code, task_timeouted

    task_stop_time = time.time() + timeout

    def killer_for_task(task, task_stop_time):
        while task.poll() is None and time.time() < task_stop_time:
            time.sleep(0.1)
        if time.time() > task_stop_time:
            try:
                task.kill()
                try:
                    task.stdout.close()
                except (ValueError, IOError) as e:
                    pass
            except OSError:
                pass

    killer_job = threading.Thread(target=killer_for_task, args=(task, task_stop_time))
    killer_job.start()

    # Wait for subprocess complete. Timeout is controlled by thread killer_job
    try:
        output = task.communicate()[0]

    except ValueError:
        pass

    killer_job.join()
    FNULL.close()

    if time.time() >= task_stop_time:
        task_timeouted = True
    else:
        task_return_code = task.returncode

    try:
        task.stdout.close()
    except ValueError:
        pass

    return output.decode('utf-8'), task_return_code, task_timeouted


def get_disk_dictionary():
    """
    function returns dict in format:
    {kernel_disk_name: [admin_disk_name, disk_description]}

    emulates this commands:
    # /usr/bin/iostat -E | grep Soft | awk '{ print $1}' > /tmp/a;
    # /usr/bin/iostat -En | grep Soft|awk '{ print $1 }' > /tmp/b; paste /tmp/a /tmp/b
    # /usr/bin/rm /tmp/a /tmp/b
    """

    disk_dictionary = {}
    iostatE, iostatE_return_code, iostatE_timeouted = run_shell_command('/usr/bin/iostat -E', 4)
    iostatEn, iostatEn_return_code, iostatEn_timeouted = run_shell_command('/usr/bin/iostat -En', 4)

    if iostatE_timeouted is False and iostatE_return_code == 0 and iostatEn_timeouted is False and iostatEn_return_code == 0:
        iostatE_lines = iostatE.splitlines()
        kernel_disk_name = []
        for iostatE_line in iostatE_lines:
            if "Soft" in iostatE_line:
                diskstrings = iostatE_line.split()
                kernel_disk_name.append(diskstrings[0])

        iostatEn_lines = iostatEn.splitlines()
        admin_disk_name = []
        j = 0
        for iostatEn_line in iostatEn_lines:
            if "Soft" in iostatEn_line:
                diskstrings = iostatEn_line.split()
                admin_disk_name.append(diskstrings[0])
            elif "Vendor" in iostatEn_line:
                one_disk_desc = re.sub(r'Vendor: (.*[^ ]) *Product: (.*[^ ]) *(Revision|Size).*', r'\1 \2',
                                       iostatEn_line)
                one_disk_desc = re.sub(r' +', ' ', one_disk_desc)  # replace double spaces by one space
                disk_dictionary.update({kernel_disk_name[j]: [admin_disk_name[j], one_disk_desc]})
                j += 1
    return (disk_dictionary)


class NetworkCollector(object):
    """
    Network Interfaces stats
    """
    # timeout how match seconds is allowed to collect data
    max_time_to_run = 4
    NetworkCollector_Timeouts = Counter('solaris_exporter_network_usage_timeouts',
                                        'Number of times when collector ran' +
                                        ' more than ' + str(max_time_to_run) + ' seconds')
    NetworkCollector_Errors = Counter('solaris_exporter_network_usage_errors', 'Number of times when collector ran' +
                                      ' with errors')
    network_collector_run_time = Gauge('solaris_exporter_network_usage_processing', 'Time spent processing request')

    def collect_unused(self):
        with self.network_collector_run_time.time():
            output, task_return_code, task_timeouted = run_shell_command('kstat -p -c net :::*bytes64',
                                                                         self.max_time_to_run)
            if task_return_code == 0 and task_timeouted is False:
                lines = output.splitlines()
                network_usage = CounterMetricFamily("solaris_exporter_network_usage", 'kstat counters',
                                                    labels=['driver', 'name', 'statistic', 'host'])
                for line in lines:
                    kstatkeyvalue = line.split("\t")
                    kstatkeyvalue[0] = re.sub('[ ,!=]', '_', kstatkeyvalue[0]).replace(",", ".")
                    kstatkey = kstatkeyvalue[0].split(":")
                    driver = kstatkey[0]
                    # instance = kstatkey[1]
                    name = kstatkey[2]
                    statistic = kstatkey[3].replace('obytes', 'output-bytes').replace('rbytes', 'input-bytes').replace(
                        'odropbytes', 'output-dropped-bytes').replace('idropbytes', 'input-dropped-bytes')
                    value = kstatkeyvalue[1]
                    if value == "" or name == "class":
                        continue
                    network_usage.add_metric([driver, name, statistic, host_name], value)
            else:
                self.NetworkCollector_Errors.inc()
                if task_timeouted:
                    self.NetworkCollector_Timeouts.inc()
        yield network_usage

    def collect(self):
        with self.network_collector_run_time.time():
            try:
                net_stats = psutil.net_io_counters(pernic=True)
            except RuntimeError:
                self.NetworkCollector_Errors.inc()
            else:
                network_usage = CounterMetricFamily("solaris_exporter_network_usage", 'kstat counters',
                                                    labels=['NIC', 'statistic', 'host'])
                for NIC in net_stats:
                    network_usage.add_metric([NIC, 'bytes_sent', host_name], net_stats[NIC].bytes_sent)
                    network_usage.add_metric([NIC, 'bytes_recv', host_name], net_stats[NIC].bytes_recv)
                    network_usage.add_metric([NIC, 'errin', host_name], net_stats[NIC].errin)
                    network_usage.add_metric([NIC, 'errout', host_name], net_stats[NIC].errout)
                    network_usage.add_metric([NIC, 'dropin', host_name], net_stats[NIC].dropin)
                    network_usage.add_metric([NIC, 'dropout', host_name], net_stats[NIC].dropout)
            yield network_usage


class DiskIOCollector(object):
    """
    Disk IO Stats
    """
    # timeout how match seconds is allowed to collect data
    max_time_to_run = 4
    disk_io_collector_timeouts = Counter('solaris_exporter_diskio_usage_timeouts',
                                         'Number of times when collector ran' +
                                         ' more than ' + str(max_time_to_run) + ' seconds')
    disk_io_collector_errors = Counter('solaris_exporter_diskio_usage_errors', 'Number of times when collector ran' +
                                       ' with errors')
    disk_io_collector_run_time = Gauge('solaris_exporter_diskio_usage_processing', 'Time spent processing request')

    def collect(self):
        with self.disk_io_collector_run_time.time():
            output, task_return_code, task_timeouted = run_shell_command('kstat -p -c disk', self.max_time_to_run)
            disk_io_usage = CounterMetricFamily("solaris_exporter_diskio_usage", 'kstat counters',
                                                labels=['driver', 'name', 'statistic', 'stat_desc',
                                                        'admin_name', 'admin_desc', 'host'])
            if task_return_code == 0 and task_timeouted is False:
                lines = output.splitlines()
                for line in lines:
                    kstatkeyvalue = line.split("\t")
                    kstatkeyvalue[0] = re.sub('[ ,!=]', '_', kstatkeyvalue[0]).replace(",", ".")
                    kstatkey = kstatkeyvalue[0].split(":")
                    driver = kstatkey[0]
                    # instance = kstatkey[1]
                    name = kstatkey[2]
                    statistic = kstatkey[3]
                    value = kstatkeyvalue[1]

                    # skip useless values
                    if value == "" or value == "disk":
                        continue
                    # skip useless statistic
                    if statistic in ['wlastupdate', 'rlastupdate', 'rcnt', 'wcnt', 'crtime', 'snaptime']:
                        continue

                    # resolve admin_name and admin_desc via dictionary
                    try:
                        admin_name = disk_dictionary[name][0]
                        admin_desc = disk_dictionary[name][1]
                    except KeyError:
                        admin_name = "unknown"
                        admin_desc = "unknown"

                    # resolve stat_desc via dictionary
                    try:
                        stat_desc = disk_operations_dictionary[statistic]
                    except KeyError:
                        stat_desc = "unknown"

                    disk_io_usage.add_metric([driver, name, statistic, stat_desc, admin_name, admin_desc,
                                              host_name], float(value))
            else:
                self.disk_io_collector_errors.inc()
                if task_timeouted:
                    self.disk_io_collector_timeouts.inc()
            yield disk_io_usage


class DiskErrorCollector(object):
    """
    Disk Error Stats
    """
    # timeout how match seconds is allowed to collect data
    max_time_to_run = 4
    disk_er_collector_timeouts = Counter('solaris_exporter_disk_error_collector_timeouts',
                                         'Number of times when collector ran' +
                                         ' more than ' + str(max_time_to_run) + ' seconds')
    disk_er_collector_errors = Counter('solaris_exporter_disk_error_collector_errors',
                                       'Number of times when collector ran' +
                                       ' with errors')
    disk_er_collector_run_time = Gauge('solaris_exporter_disk_errors_collector_processing',
                                       'Time spent processing request')

    def collect(self):
        with self.disk_er_collector_run_time.time():
            output, task_return_code, task_timeouted = run_shell_command('kstat -p -c device_error :::/.*Errors/',
                                                                         self.max_time_to_run)
            disk_errors = CounterMetricFamily("solaris_exporter_disk_errors", 'kstat counters',
                                              labels=['driver', 'name', 'statistic',
                                                      'admin_name', 'admin_desc', 'host'])
            if task_return_code == 0 and task_timeouted is False:
                lines = output.splitlines()

                for line in lines:
                    kstatkeyvalue = line.split("\t")  # sderr:58:sd58,err:Transport Errors
                    kstatkeyvalue[0] = re.sub('[ ,!=]', '_', kstatkeyvalue[0]).replace(",", ".")
                    kstatkey = kstatkeyvalue[0].split(":")
                    module = kstatkey[0].replace('err', '')
                    # instance = kstatkey[1]
                    name = kstatkey[2].replace('_err', '')
                    statistic = kstatkey[3]
                    value = kstatkeyvalue[1]

                    # resolve admin_name and admin_desc via dictionary
                    try:
                        admin_name = disk_dictionary[name][0]
                        admin_desc = disk_dictionary[name][1]
                    except KeyError:
                        admin_name = "unknown"
                        admin_desc = "unknown"

                    disk_errors.add_metric([module, name, statistic, admin_name, admin_desc,
                                            host_name], float(value))
            else:
                self.disk_er_collector_errors.inc()
                if task_timeouted:
                    self.disk_er_collector_timeouts.inc()
            yield disk_errors


class CpuLoadCollector(object):
    """
    CPU load average 1, 5, 15 min, cpu count
    """
    cpu_load_collector_run_time = Gauge('solaris_exporter_cpu_load_processing', 'Time spent processing request')

    def collect(self):
        with self.cpu_load_collector_run_time.time():
            worker_stat_cpu_load = GaugeMetricFamily('solaris_exporter_cpu_load',
                                                     'python psutil counters, system load avg.',
                                                     labels=['host', 'statistic'])
            cpuinfo = os.getloadavg()
            worker_stat_cpu_load.add_metric([host_name, 'load1m'], cpuinfo[0])
            worker_stat_cpu_load.add_metric([host_name, 'load5m  '], cpuinfo[1])
            worker_stat_cpu_load.add_metric([host_name, 'load15m'], cpuinfo[2])
            cpuinfo = len(psutil.cpu_percent(interval=None, percpu=True))
            worker_stat_cpu_load.add_metric([host_name, 'vcpu'], cpuinfo)
        yield worker_stat_cpu_load


class CpuTimeCollector(object):
    """
    CPU time may be translated in percent later
    """
    cpu_time_collector_run_time = Gauge('solaris_exporter_cpu_time_processing', 'Time spent processing request')

    def collect(self):
        with self.cpu_time_collector_run_time.time():
            worker_stat_cpu_time = CounterMetricFamily('solaris_exporter_cpu_time',
                                                       'python psutil counters, CPU usage time.',
                                                       labels=['host', 'statistic'])
            cpuinfo = psutil.cpu_times(percpu=False)
            worker_stat_cpu_time.add_metric([host_name, 'user'], cpuinfo.user)
            worker_stat_cpu_time.add_metric([host_name, 'system'], cpuinfo.system)
            worker_stat_cpu_time.add_metric([host_name, 'idle'], cpuinfo.idle)
            worker_stat_cpu_time.add_metric([host_name, 'oiwait'], cpuinfo.iowait)
        yield worker_stat_cpu_time


class MemCollector(object):
    """
    Memory and SWAP Stats
    """
    mem_collector_run_time = Gauge('solaris_exporter_MemCollector_processing', 'Time spent processing request')

    def collect(self):
        with self.mem_collector_run_time.time():
            worker_stat_mem = GaugeMetricFamily('solaris_exporter_memory_usage_bytes',
                                                'python psutil counters, Memory usage in bytes.',
                                                labels=['host', 'type', 'counter'])
            ram = psutil.virtual_memory()
            worker_stat_mem.add_metric([host_name, 'virtual', 'used'], ram.used)
            worker_stat_mem.add_metric([host_name, 'virtual', 'available'], ram.available)
            worker_stat_mem.add_metric([host_name, 'virtual', 'total'], ram.total)
            worker_stat_mem.add_metric([host_name, 'virtual', 'free'], ram.free)

            #try:
            #    swap = psutil.swap_memory()
            #except ValueError:
                # print('old version of psutil module, skipping swap stat, you need to update it to 5.9.0+ and run '
                #       'Python3.7')
            # see https://github.com/n27051538/solaris_exporter/issues/7
            swap = psutil_local_swap_memory()

            worker_stat_mem.add_metric([host_name, 'swap', 'total'], swap.total)
            worker_stat_mem.add_metric([host_name, 'swap', 'used'], swap.used)
            worker_stat_mem.add_metric([host_name, 'swap', 'free'], swap.free)
            worker_stat_mem.add_metric([host_name, 'swap', 'sin'], swap.sin)
            worker_stat_mem.add_metric([host_name, 'swap', 'sout'], swap.sout)


        yield worker_stat_mem


# this code is rewritten psutil.disk_partitions() due to bug with nfs mounted in local zones
# https://github.com/giampaolo/psutil/issues/1674
# later it was simplified as using cext.disk_partitions() in my code.

# from psutil import _psposix
# from psutil import _psutil_sunos as cext
# from psutil import _common
# disk_usage = _psposix.disk_usage
#
# def my_disk_partitions(all=False):
#     """Return system disk partitions.
#     This function is rewritten psutils.disk_partitions() due to its bug
#     with mounted NFS folders into solaris localzones. Now we have try-except OSError 'Not owner'
#     arround disk_usage()
#     """
#     retlist = []
#     partitions = cext.disk_partitions()
#     for partition in partitions:
#         device, mountpoint, fstype, opts = partition
#         if device == 'none':
#             device = ''
#         if not all:
#             try:
#                 if not disk_usage(mountpoint).total:
#                     continue
#             except OSError:
#                 continue
#
#         ntuple = _common.sdiskpart(device, mountpoint, fstype, opts)
#         retlist.append(ntuple)
#     return retlist

# This code is rewritten psutil.swap_memory() due to bug with swap -l in Solaris 11.4.41 due to
# changes in swap -l output. Also now we are ignoring swap device absence.
def psutil_local_swap_memory():
    """Report swap memory metrics."""
    page_size = os.sysconf('SC_PAGE_SIZE')
    sin, sout = cext.swap_mem()
    FNULL = open(os.devnull, 'w')
    p = subprocess.Popen(['/usr/bin/env', 'PATH=/usr/sbin:/sbin:%s' %
                          os.environ['PATH'], 'swap', '-l'],
                         stdout=subprocess.PIPE, stderr=FNULL)
    stdout, stderr = p.communicate()
    FNULL.close()
    stdout = stdout.decode('utf-8')
    if p.returncode != 0:
        total = free = 0
        # raise RuntimeError("'swap -l' failed (retcode=%s)" % p.returncode)
    else:
        lines = stdout.strip().split('\n')[1:]
        # if not lines:
        #    raise RuntimeError('no swap device(s) configured')
        total = free = 0
        for line in lines:
            line = line.split()
            t, f = line[3:5]
            total += int(int(t) * 512)
            free += int(int(f) * 512)
    used = total - free

    try:
        percent = (float(used) / total) * 100
    except ZeroDivisionError:
        percent = 0.0

    sswap = namedtuple('sswap', ['total', 'used', 'free', 'percent', 'sin', 'sout'])
    return sswap(total, used, free, percent, sin * page_size, sout * page_size)


class DiskSpaceCollector(object):
    """
    Disk space stats
    Note that UFS inode info is NOT collected.
    """
    disk_space_collector_run_time = Gauge('solaris_exporter_diskspace_worker', 'Time spent processing request')

    def collect(self):
        with self.disk_space_collector_run_time.time():
            worker_stat_space = GaugeMetricFamily('solaris_exporter_diskspace_usage_bytes',
                                                  'python psutil counters, diskspace usage in bytes.',
                                                  labels=['host', 'statistic', 'mountpoint', 'device', 'fstype', ])

            # disk_partitions = my_disk_partitions(all=False)   # rewritten due to bug: https://github.com/giampaolo/psutil/issues/1674
            disk_partitions = cext.disk_partitions()
            for partition in disk_partitions:
                device, mountpoint, fstype, opts = partition
                if fstype not in ['zfs', 'ufs']:
                    continue
                if '/VARSHARE' in device:
                    continue
                try:
                    spaceinfo = psutil.disk_usage(mountpoint)
                except OSError:
                    continue
                worker_stat_space.add_metric([host_name, 'used', mountpoint, device, fstype], spaceinfo.used)
                worker_stat_space.add_metric([host_name, 'total', mountpoint, device, fstype], spaceinfo.total)
                worker_stat_space.add_metric([host_name, 'free', mountpoint, device, fstype], spaceinfo.free)
                worker_stat_space.add_metric([host_name, 'percent', mountpoint, device, fstype], spaceinfo.percent)
        yield worker_stat_space


class CurTimeCollector(object):
    """
    current_time - For Dirty comparation with Prometheus server time.
    """

    def collect(self):
        cur_time_metric_family = CounterMetricFamily('solaris_exporter_current_time_seconds', 'Current time of system',
                                                     labels=[])
        cur_time_metric_family.add_metric([], time.time())
        yield cur_time_metric_family


class UpTimeCollector(object):
    """
    uptime - for reboot alarming.
    """

    def collect(self):
        uptime_metric_family = CounterMetricFamily('solaris_exporter_uptime_seconds', 'uptime of system', labels=[])
        uptime_metric_family.add_metric([], time.time() - psutil.boot_time())
        yield uptime_metric_family


def get_pset_dictionary():
    """
    Returns pset dictionary: {'pset_num': 'cpu_count_in_pset'}, example:  {'0': '144'}
    """
    pset_dictionary = {}

    output, return_code, timeouted = run_shell_command("kstat -p -c misc unix::pset:ncpus", 5)
    lines = output.splitlines()
    for line in lines:
        kstatkeyvalue = line.split("\t")
        kstatkeyvalue[0] = re.sub('[ ,!=]', '_', kstatkeyvalue[0]).replace(",", ".")
        kstatkey = kstatkeyvalue[0].split(":")
        # kstatkey[0] always set to 'unix'
        pset_number = kstatkey[1]
        # kstatkey[2] always set to 'pset'
        # kstatkey[3] always set to 'ncpus'
        value = kstatkeyvalue[1]  # cpu number in pset
        pset_dictionary[pset_number] = float(value)
    return pset_dictionary


class PerZoneCpuCollector(object):
    """
    Solaris Zones CPU Usage with processor sets info and zone activity stats
    """
    # timeout how match seconds is allowed to collect data
    max_time_to_run = 25
    per_zone_cpu_collector_timeouts = Counter('solaris_exporter_per_zone_cpu_timeouts',
                                              'Number of times when collector ran' +
                                              ' more than ' + str(max_time_to_run) + ' seconds')
    per_zone_cpu_collector_errors = Counter('solaris_exporter_per_zone_cpu_errors',
                                            'Number of times when collector ran with errors')
    per_zone_cpu_collector_run_time = Gauge('solaris_exporter_per_zone_cpu_processing', 'Time spent processing request')

    def collect(self):
        with self.per_zone_cpu_collector_run_time.time():
            per_zone_usage = CounterMetricFamily("solaris_exporter_per_zone_usage_total", 'kstat counters',
                                                 labels=['zone', 'statistic', 'stat_desc', 'pset', 'host'])
            per_zone_usage_dict = {}  # will be nested dict
            zonename_dict = {}
            zone_pset_dict = {}
            query = ''
            for counter in per_zone_cpu_counters_dictionary:
                query += "|^" + counter + "$"
            query = "-c zones cpu::/^sys_zone_*/:/(" + query[1:] + "|^zonename$)/"
            # print('kstat -p '+query)
            output, task_return_code, task_timeouted = run_shell_command('kstat -p ' + query, self.max_time_to_run)
            if task_return_code == 0 and task_timeouted is False:
                lines = output.splitlines()
                for line in lines:
                    kstatkeyvalue = line.split("\t")
                    kstatkeyvalue[0] = re.sub('[ ,!=]', '_', kstatkeyvalue[0]).replace(",", ".")
                    kstatkey = kstatkeyvalue[0].split(":")
                    # kstatkey[0]            # always set to 'cpu'
                    # kstatkey[1]            # zone_sys_number or cpu_number
                    # kstatkey[2]            # 'sys_zone_21' or 'sys_zone_accum' or 'sys_zone_pset_0_accum'
                    if kstatkey[2].startswith('sys_zone_pset_'):
                        zone_pset_number = re.sub(r'sys_zone_pset_([0-9]+)_accum', r'\1', kstatkey[2])
                        zone_sys_number = kstatkey[1]
                        zone_pset_dict[zone_sys_number] = zone_pset_number
                        continue
                    elif kstatkey[2] == 'sys_zone_accum':
                        continue
                    zone_sys_number = re.sub(r'^sys_zone_([0-9]+)$', r'\1', kstatkey[2])
                    statistic = kstatkey[3]
                    value = kstatkeyvalue[1]
                    if statistic == 'zonename':
                        zonename_dict[zone_sys_number] = value
                        continue
                    # create new nested dictionary for zone_sys_name, or preserve it if it exists
                    per_zone_usage_dict[zone_sys_number] = per_zone_usage_dict.get(zone_sys_number, {})
                    # add value to nested dictionary of statistic for zone_sys_name
                    per_zone_usage_dict[zone_sys_number][statistic] = \
                        per_zone_usage_dict[zone_sys_number].get(statistic, 0.0) + float(value)
                # evacuate stored in dictionaries info into metrics
                for zone_sys_number in per_zone_usage_dict.keys():
                    for statistic in per_zone_usage_dict[zone_sys_number].keys():
                        local_zone_name = zonename_dict.get(zone_sys_number, 'sys_zone_' + zone_sys_number)
                        pset_number = zone_pset_dict.get(zone_sys_number, 'unknown')
                        stat_desc = per_zone_cpu_counters_dictionary.get(statistic, 'unknown')
                        value = per_zone_usage_dict.get(zone_sys_number, {}).get(statistic, 0.0)
                        if statistic in ['cpu_nsec_kernel', 'cpu_nsec_user']:
                            statistic = statistic[9:]
                            cpus_in_pset = pset_dictionary.get(pset_number, 0)
                            try:
                                value = value / cpus_in_pset / 1000000000  # translate nsec in sec
                            except ZeroDivisionError:
                                value = 0
                        per_zone_usage.add_metric([local_zone_name, statistic, stat_desc, pset_number, host_name],
                                                  value)
                    per_zone_usage.add_metric([local_zone_name, 'cpus', 'cpu number in pset', pset_number, host_name],
                                              cpus_in_pset)
            else:
                self.per_zone_cpu_collector_errors.inc()
                if task_timeouted:
                    self.per_zone_cpu_collector_timeouts.inc()
        yield per_zone_usage


class PerZoneCapsCollector(object):
    """
    Solaris Zones Virtual Memory (SWAP) Resource Capping, current nprocs number in zones
    """
    # timeout how match seconds is allowed to collect data
    max_time_to_run = 25
    per_zone_caps_collector_timeouts = Counter('solaris_exporter_per_zone_caps_timeouts',
                                               'Number of times when collector ran' +
                                               ' more than ' + str(max_time_to_run) + ' seconds')
    per_zone_caps_collector_errors = Counter('solaris_exporter_per_zone_caps_errors',
                                             'Number of times when collector ran with errors')
    per_zone_caps_collector_run_time = Gauge('solaris_exporter_per_zone_caps_processing',
                                             'Time spent processing request')

    def collect(self):
        with self.per_zone_caps_collector_run_time.time():
            per_zone_caps = GaugeMetricFamily("solaris_exporter_per_zone_caps_total",
                                              'kstat counters about zone resources',
                                              labels=['zone', 'statistic', 'host'])
            per_zone_caps_dict = {}  # will be nested dict
            zonename_dict = {}
            query = "-c zone_caps caps::/^swapresv_zone_[0-9]+$/:/^(usage|value|zonename)$/ caps::/^nprocs_zone_[0-9]+$/:usage"
            # print('kstat -p '+query)
            output, task_return_code, task_timeouted = run_shell_command('kstat -p ' + query, self.max_time_to_run)
            if task_return_code == 0 and task_timeouted is False:
                lines = output.splitlines()
                for line in lines:
                    kstatkeyvalue = line.split("\t")
                    kstatkeyvalue[0] = re.sub('[ ,!=]', '_', kstatkeyvalue[0]).replace(",", ".")
                    kstatkey = kstatkeyvalue[0].split(":")
                    # kstatkey[0]            # always set to 'caps'
                    # kstatkey[1]            # zone_sys_number
                    # kstatkey[2]            # 'swapresv_zone_28' or 'nprocs_zone_18'
                    # kstatkey[3]            # 'zonename', 'usage' or 'value' text
                    zone_sys_number = kstatkey[1]
                    value = kstatkeyvalue[1]

                    if kstatkey[2].startswith('nprocs_zone'):
                        statistic = 'nprocs_current'
                    else:
                        if kstatkey[3] == 'value':
                            statistic = 'swap_limit_bytes'
                        elif kstatkey[3] == 'usage':
                            statistic = 'swap_usage_bytes'
                    if kstatkey[3] == 'zonename':
                        zonename_dict[zone_sys_number] = value
                        continue
                    # create new nested dictionary for zone_sys_name, or preserve it if it exists
                    per_zone_caps_dict[zone_sys_number] = per_zone_caps_dict.get(zone_sys_number, {})
                    # add value to nested dictionary of statistic for zone_sys_name
                    per_zone_caps_dict[zone_sys_number][statistic] = float(value)
                # evacuate stored in dictionaries info into metrics
                for zone_sys_number in per_zone_caps_dict.keys():
                    for statistic in per_zone_caps_dict[zone_sys_number].keys():
                        local_zone_name = zonename_dict.get(zone_sys_number, 'sys_zone_' + zone_sys_number)
                        value = per_zone_caps_dict.get(zone_sys_number, {}).get(statistic, 0.0)
                        per_zone_caps.add_metric([local_zone_name, statistic, host_name], value)
            else:
                self.per_zone_caps_collector_errors.inc()
                if task_timeouted:
                    self.per_zone_caps_collector_timeouts.inc()
        yield per_zone_caps


class FCinfoCollector(object):
    """
    FC links Multipath
    """
    # timeout how match seconds is allowed to collect data
    max_time_to_run = 4
    fc_lun_collector_timeouts = Counter('solaris_exporter_fc_paths_timeouts',
                                        'timeouts')
    fc_lun_collector_errors = Counter('solaris_exporter_fc_paths_errors', 'Number of times when collector ran' +
                                      ' with errors')
    fc_lun_collector_run_time = Gauge('solaris_exporter_fc_paths_processing', 'Time spent processing request')

    def collect(self):
        with self.fc_lun_collector_run_time.time():
            output, task_return_code, task_timeouted = run_shell_command('/usr/sbin/mpathadm list lu',
                                                                         self.max_time_to_run)
            if task_return_code == 0 and task_timeouted is False:
                lines = output.splitlines()
                fc_lun = GaugeMetricFamily("solaris_exporter_fc_paths", '/usr/sbin/mpathadm list lu',
                                           labels=['device', 'stat', 'host'])
                fc_total_paths = {}
                fc_active_paths = {}
                for line in lines:
                    content = line.strip()
                    if '/dev/rdsk/' in content:
                        device = re.sub(r'/dev/rdsk/(.*)s2', r'\1', content)
                    elif 'Total Path Count' in content:
                        content = content.split(':')
                        fc_total_paths[device] = content[1]
                    elif 'Operational Path Count:' in content:
                        content = content.split(':')
                        fc_active_paths[device] = content[1]
                    else:
                        device = "unknown"
                for device in fc_total_paths.keys():
                    if device == "unknown":
                        continue
                    fc_lun.add_metric([device, 'active', host_name], float(fc_active_paths.get(device, 0)))
                    fc_lun.add_metric([device, 'total', host_name], float(fc_total_paths.get(device, 0)))
                yield fc_lun
            else:
                self.fc_lun_collector_errors.inc()
                if task_timeouted:
                    self.fc_lun_collector_timeouts.inc()


class SVCSCollector(object):
    """
    'svcs -x' checker
    """
    # timeout how match seconds is allowed to collect data
    max_time_to_run = 4
    svcs_x_collector_timeouts = Counter('solaris_exporter_svcs_x_timeouts',
                                        'timeouts')
    svcs_x_collector_errors = Counter('solaris_exporter_svcs_x_errors', 'Number of times when collector ran' +
                                      ' with errors')
    svcs_x_collector_run_time = Gauge('solaris_exporter_svcs_x_processing', 'Time spent processing request')

    def collect(self):
        with self.svcs_x_collector_run_time.time():
            output, task_return_code, task_timeouted = run_shell_command('/usr/bin/svcs -x',
                                                                         self.max_time_to_run)
            if task_return_code == 0 and task_timeouted is False:
                lines = output.splitlines()
                svcs_x = GaugeMetricFamily("solaris_exporter_svcs_x_failed_services",
                                           'failed services counter in svcs -x',
                                           labels=['host'])
                svcs_fail = 0
                for line in lines:
                    if line.strip().startswith('svc:'):
                        svcs_fail += 1
                svcs_x.add_metric([host_name], float(svcs_fail))
            else:
                self.svcs_x_collector_errors.inc()
                if task_timeouted:
                    self.svcs_x_collector_timeouts.inc()
        yield svcs_x


class FmadmCollector(object):
    """
    'fmadm faulty' checker
    """
    # timeout how match seconds is allowed to collect data
    max_time_to_run = 15
    fmadm_collector_timeouts = Counter('solaris_exporter_fmadm_timeouts',
                                       'timeouts')
    fmadm_collector_errors = Counter('solaris_exporter_fmadm_errors', 'Number of times when collector ran' +
                                     ' with errors')
    fmadm_collector_run_time = Gauge('solaris_exporter_fmadm_processing', 'Time spent processing request')

    def collect(self):
        with self.fmadm_collector_run_time.time():
            output, task_return_code, task_timeouted = run_shell_command('/usr/bin/pfexec /usr/sbin/fmadm faulty',
                                                                         self.max_time_to_run)
            if task_return_code == 0 and task_timeouted is False:
                lines = output.splitlines()
                fmadm = GaugeMetricFamily("solaris_exporter_fmadm_faults", 'faults in fmadm faulty',
                                          labels=['host'])
                faults = 0
                for line in lines:
                    if line.strip().startswith('TIME'):
                        faults += 1
                fmadm.add_metric([host_name], float(faults))
                yield fmadm
            else:
                self.fmadm_collector_errors.inc()
                if task_timeouted:
                    self.fmadm_collector_timeouts.inc()


class ZpoolCollector(object):
    """
    'zpool status' checker
    """
    # timeout how match seconds is allowed to collect data
    max_time_to_run = 4
    zpool_collector_timeouts = Counter('solaris_exporter_zpool_timeouts',
                                       'timeouts')
    zpool_collector_errors = Counter('solaris_exporter_zpool_errors', 'Number of times when collector ran' +
                                     ' with errors')
    zpool_collector_run_time = Gauge('solaris_exporter_zpool_processing', 'Time spent processing request')

    def collect(self):
        with self.zpool_collector_run_time.time():
            output, task_return_code, task_timeouted = run_shell_command('/usr/sbin/zpool status',
                                                                         self.max_time_to_run)
            if task_return_code == 0 and task_timeouted is False:
                lines = output.splitlines()
                zpool = GaugeMetricFamily("solaris_exporter_zpool_faults", 'faults in zpool status',
                                          labels=['host'])
                faults = 0
                for line in lines:
                    line = line.strip()
                    if any(s in line for s in ['FAILED', 'DEGRADED']):
                        faults += 1
                zpool.add_metric([host_name], float(faults))
                yield zpool
            else:
                self.zpool_collector_errors.inc()
                if task_timeouted:
                    self.zpool_collector_timeouts.inc()


class MetaStatCollector(object):
    """
    'metastat -a' checker
    """
    # timeout how match seconds is allowed to collect data
    max_time_to_run = 5
    metastat_collector_timeouts = Counter('solaris_exporter_metastat_timeouts',
                                          'timeouts')
    metastat_collector_errors = Counter('solaris_exporter_metastat_errors', 'Number of times when collector ran' +
                                        ' with errors')
    metastat_collector_run_time = Gauge('solaris_exporter_metastat_processing', 'Time spent processing request')

    def collect(self):
        with self.metastat_collector_run_time.time():
            output, task_return_code, task_timeouted = run_shell_command('/usr/sbin/metastat -a',
                                                                         self.max_time_to_run)
            if task_return_code == 0 and task_timeouted is False:
                lines = output.splitlines()
                metastat = GaugeMetricFamily("solaris_exporter_metastat_faults", 'faults in metastat',
                                             labels=['host'])
                faults = 0
                for line in lines:
                    line = line.strip()
                    if any(s in line for s in ['Needs maintenance', 'Last erred', 'Unavailable']):
                        faults += 1
                metastat.add_metric([host_name], float(faults))
                yield metastat
            else:
                self.metastat_collector_errors.inc()
                if task_timeouted:
                    self.metastat_collector_timeouts.inc()


class MetaDBCollector(object):
    """
    'metadb' checker
    """
    # timeout how match seconds is allowed to collect data
    max_time_to_run = 5
    metadb_collector_timeouts = Counter('solaris_exporter_metadb_timeouts',
                                        'timeouts')
    metadb_collector_errors = Counter('solaris_exporter_metadb_errors', 'Number of times when collector ran' +
                                      ' with errors')
    metadb_collector_run_time = Gauge('solaris_exporter_metadb_processing', 'Time spent processing request')

    def collect(self):
        with self.metadb_collector_run_time.time():
            output, task_return_code, task_timeouted = run_shell_command('/usr/sbin/metadb',
                                                                         self.max_time_to_run)
            if task_return_code == 0 and task_timeouted is False:
                lines = output.splitlines()
                metadb = GaugeMetricFamily("solaris_exporter_metadb_faults", 'faults in metadb',
                                           labels=['host'])
                faults = 0
                for line in lines:
                    line = line.strip()
                    if any(s in line for s in ['W', 'D', 'M']):
                        faults += 1
                metadb.add_metric([host_name], float(faults))
                yield metadb
            else:
                self.metadb_collector_errors.inc()
                if task_timeouted:
                    self.metadb_collector_timeouts.inc()


class PrtdiagCollector(object):
    """
    'prtdiag' checker
    """
    # timeout how match seconds is allowed to collect data
    max_time_to_run = 50
    prtdiag_collector_timeouts = Counter('solaris_exporter_prtdiag_timeouts', 'timeouts')
    prtdiag_collector_run_time = Gauge('solaris_exporter_prtdiag_processing', 'Time spent processing request')

    its_time_to_run_now = 0
    # repeat prtdiag only after each 60 times, write result from cache instead (prtdiag is heavy)
    repeat_prtdiag_after_times = 60

    def collect(self):
        global prtdiag_return_code
        global prtdiag_timeouted
        if self.its_time_to_run_now == 0:
            with self.prtdiag_collector_run_time.time():
                prtdiag_output, prtdiag_return_code, prtdiag_timeouted = run_shell_command('/usr/sbin/prtdiag -v',
                                                                                           self.max_time_to_run)
                if prtdiag_timeouted is True:
                    self.prtdiag_collector_timeouts.inc()
        self.its_time_to_run_now += 1
        self.its_time_to_run_now %= self.repeat_prtdiag_after_times

        if prtdiag_timeouted is False:
            prtdiag = GaugeMetricFamily("solaris_exporter_prtdiag_rc", 'prtdiag return code', labels=['host'])
            prtdiag.add_metric([host_name], float(prtdiag_return_code))
            yield prtdiag


class TextFileCollector(object):
    """
    Read Input from a textfile to include in output. Thanks to Marcel Peter
    """
    TextFileCollector_run_time = Gauge('solaris_exporter_textfile_processing', 'Time spent processing request')

    def collect(self):
        with self.TextFileCollector_run_time.time():
            fpath = text_file_path
            fnames = glob(fpath + '*.prom')
            for file_name_r in fnames:
                # filename to open for read
                with open(file_name_r, 'r') as text_object:
                    output = text_object.read()
                    for family in text_string_to_metric_families(output):
                        yield family
                    text_object.close


# replace start_http_server() method to capture error messages in my_http_error_handler()
# remove this to revert to prometheus_client.start_http_server

try:
    # Python 2.7
    from BaseHTTPServer import HTTPServer
    from SocketServer import ThreadingMixIn
except ImportError:
    # Python 3
    from http.server import HTTPServer
    from socketserver import ThreadingMixIn

from prometheus_client import MetricsHandler


class _ThreadingSimpleServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


def start_http_server(port, addr='', registry=REGISTRY):
    """Starts an HTTP server for prometheus metrics as a daemon thread"""

    def my_http_error_handler(request, client_address):
        print('Request from ' + client_address[0] + ':' + str(client_address[1]) + ' dropped. Broken pipe.')

    CustomMetricsHandler = MetricsHandler.factory(registry)
    httpd = _ThreadingSimpleServer((addr, port), CustomMetricsHandler)
    httpd.handle_error = my_http_error_handler
    t = threading.Thread(target=httpd.serve_forever)
    t.daemon = True
    t.start()


# end of replace start_http_server()


if __name__ == '__main__':
    assert psutil.SUNOS, 'This program is for Solaris OS only. See installation doc in its header'
    host_name = socket.gethostname()

    # this will be refreshed once in dictionaries_refresh_interval_sec
    disk_dictionary = get_disk_dictionary()
    pset_dictionary = get_pset_dictionary()

    prtdiag_return_code = 0
    prtdiag_timeouted = False

    # collectors enabled for all zones:
    collectors = [
        CurTimeCollector(),
        UpTimeCollector(),
        NetworkCollector(),
        DiskSpaceCollector(),
        SVCSCollector(),
        TextFileCollector(),
    ]

    zones, rc, timeouted = run_shell_command('/usr/sbin/zoneadm list -icp', 3)
    nzones = 0
    if rc == 0 and not timeouted:
        zones = zones.splitlines()
        for line in zones:
            zone = line.split(':')
            # print(zone)
            zone = zone[1]
            if zone != "global":
                nzones += 1

    zonename, rc, timeouted = run_shell_command('/usr/bin/zonename', 3)
    zonename = zonename.strip()
    if zonename == "global":
        collectors.extend([
            CpuLoadCollector(),
            CpuTimeCollector(),
            MemCollector(),
            DiskIOCollector(),
            DiskErrorCollector(),
            ZpoolCollector(),
            FCinfoCollector(),
            FmadmCollector(),
            PrtdiagCollector(),
            MetaDBCollector(),
            MetaStatCollector(),
        ])

    # enable zone collectors only if global zones have localzones or we are running inside localzone
    if nzones > 0 or zonename != "global":
        collectors.extend([
            PerZoneCpuCollector(),
            PerZoneCapsCollector(),
        ])

    # start webserver and register selected collectors in prometheus.client library
    start_http_server(exporter_port)
    for c in collectors:
        REGISTRY.register(c)

    while True:
        try:
            time.sleep(dictionaries_refresh_interval_sec)
            # this will be refresh dicts once in dictionaries_refresh_interval_sec
            disk_dictionary = get_disk_dictionary()
            pset_dictionary = get_pset_dictionary()
        except KeyboardInterrupt:
            print("\nExit Requested\n")
            exit()
