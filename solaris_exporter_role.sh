#!/usr/bin/bash
user=monitor
profile_name=Prometheus

uid0_commands="
/usr/sbin/fmadm
/usr/sbin/nvmeadm
/usr/sbin/raidctl
/usr/sbin/zlogin
"
# Also add priv 'file_dac_search': 'df -h' will be able to view zone filesystems
# Also add auth 'solaris.ldoms.read': 'ldm list' will be able to view domain info

current_profiles=$(profiles ${user} | egrep -v "^${user}:$|^All$|^Basic Solaris User$|^${profile_name}$")
current_profiles=$(echo -n "${current_profiles}" | tr '\n' ',')

function RemoveRole {
       usermod  -K "defaultpriv-=file_dac_search,sys_config" -A "-solaris.ldoms.read" ${user}  2>/dev/null
       usermod  -K "defaultpriv+=basic" ${user}  2>/dev/null

       for uid0_command in ${uid0_commands}; do
             cmd_string="${profile_name}::solaris:cmd:::${uid0_command}:uid=0"
             if cp /etc/security/exec_attr /tmp/pexec_attr; then
                    echo "Removing \"${cmd_string}\" from  /etc/security/exec_attr"
                    grep -v "^${cmd_string}$" /tmp/pexec_attr > /etc/security/exec_attr && rm /tmp/pexec_attr
             else
                    echo "Failed to copy /etc/security/exec_attr to temporary file /tmp/pexec_attr"
                    exit 3
             fi
       done

       profile_string="${profile_name}:::User could run some monitoring commands"
       if cp /etc/security/prof_attr /tmp/pprof_attr; then
              echo "Removing \"${profile_string}\" from /etc/security/prof_attr"
              grep -v "^${profile_string}$" /tmp/pprof_attr > /etc/security/prof_attr && rm /tmp/pprof_attr
       else
              echo "Failed to copy /etc/security/prof_attr to /tmp/pprof_attr"
       fi
       chmod 644  /etc/security/prof_attr /etc/security/exec_attr
       chown root:sys /etc/security/prof_attr /etc/security/exec_attr

       usermod -P "${current_profiles}" ${user} 2>/dev/null
       echo "Current profiles of ${user} user is: ${current_profiles}"
}

function InstallRole {
       for uid0_command in ${uid0_commands}; do
             cmd_string="${profile_name}::solaris:cmd:::${uid0_command}:uid=0"
             if grep "^${cmd_string}$" /etc/security/exec_attr >/dev/null; then
                   echo "role cmd \"${cmd_string}\" is already in /etc/security/exec_attr. skipping"
             else
                   echo "${cmd_string}" >> /etc/security/exec_attr
                   echo "\"${cmd_string}\" added in /etc/security/exec_attr"
             fi
       done

       profile_string="${profile_name}:::User could run some monitoring commands"

       if grep "^${profile_string}$" /etc/security/prof_attr >/dev/null ; then
             echo "role attr \"${profile_string}\" is already in /etc/security/prof_attr. skipping"
       else
             echo "${profile_string}"  >> /etc/security/prof_attr
             echo "\"${profile_string}\" added in /etc/security/prof_attr"
       fi

       if [[ -z "${current_profiles}" ]] ; then
              current_profiles="${profile_name}"
       else
              current_profiles="${current_profiles},${profile_name}"
       fi

       usermod -P "${current_profiles}" ${user} 2>/dev/null
       usermod  -K "defaultpriv+=basic,file_dac_search,sys_config" -A "+solaris.ldoms.read" ${user} 2>/dev/null
       echo "Current profiles of ${user} user is: ${current_profiles}"
}

if [[ "$(uname)" != "SunOS" ]] ; then echo "Only for Solaris"; exit 1; fi
if [[ ! "$(/usr/xpg4/bin/id -u)" == "0" ]] ; then echo "Only root can run this script"; exit 2; fi

if [[ "$1" == "install" ]] ; then
    InstallRole
elif [[ "$1" == "remove" ]] ; then
    RemoveRole
else
    echo "Usage: $0 {install|remove}"
    exit 4
fi
