#!/bin/bash

run_binary="solaris_exporter.py"
service_user="monitor"
service_group="monitor"

os=$(uname -r)
if [[ "$os" == "5.11" ]]; then
    python="/usr/bin/python2.7"
elif  [[ "$os" == "5.10" ]]; then
    python="/opt/csw/bin/python2.7"
else
    echo "$(uname) ${os} in unsupported."
    exit 1
fi

function InstallService {

     [[ -x ${work_dir}/${run_binary} ]] || { echo ${run_binary} not found in ${work_dir}; exit 2; }
     [[ -x ${python} ]] || { echo Python not found in ${python}; exit 3; }
     echo "Installing ${run_binary} as SMF prometheus/solaris_exporter"
     XML=$(
     cat <<EOXML
<?xml version="1.0"?>
<!DOCTYPE service_bundle SYSTEM "/usr/share/lib/xml/dtd/service_bundle.dtd.1">
<service_bundle type='manifest' name='solaris_exporter'>
    <service name='prometheus/solaris_exporter' type='service'  version='1'>
        <create_default_instance enabled='true' />
        <single_instance />
        <dependency name='multi-user' grouping='require_all' restart_on='none' type='service'>
            <service_fmri value='svc:/system/filesystem/local:default' />
            <service_fmri value='svc:/milestone/network:default' />
        </dependency>
        <exec_method type='method' name='start' exec='${python} ${work_dir}/${run_binary}' timeout_seconds='60'>
            <method_context>
                <method_credential user='${service_user}' group='${service_group}' />
                <method_environment><envvar name="LC_ALL" value="C" /></method_environment>
             </method_context>
        </exec_method>
        <exec_method type='method' name='stop' exec=':kill' timeout_seconds='60' />
        <exec_method type='method' name='refresh' exec=':true' timeout_seconds='60' />

        <property_group name='startd' type='framework'>
            <propval name='ignore_error' type='astring' value='core,signal'/>
            <propval name='duration' type='astring' value='child' />
        </property_group>
    </service>
</service_bundle>
EOXML
    )

    out_xml="${work_dir}/${run_binary}.xml"

    #create XML
    echo "${XML}" > ${out_xml} || echo ${out_xml} create failed

    #check XML syntax
    svccfg validate ${out_xml} || echo ${out_xml} failed to validate

    svccfg import ${out_xml}

    # create role settings for user
    install_role_out=$(./solaris_exporter_role.sh install)
    while read install_role_line; do
        echo "    i    ${install_role_line}"
    done < <(echo "${install_role_line}")

    #enable auto starting
    svcadm enable prometheus/solaris_exporter
    sleep 2

    #see start log of service
    #echo LOG FILE "/var/svc/log/prometheus-solaris_exporter:default.log"
    tail -7 "/var/svc/log/prometheus-solaris_exporter:default.log"

    rm ${out_xml}

    #check service creation (without headers)
    if svcs -H prometheus/solaris_exporter; then
        exit 0
    else
        exit 7
    fi
}

function RemoveService {

    remove_role_line=$(./solaris_exporter_role.sh remove)
    while read install_role_line; do
        echo "     r    ${install_role_line}"
    done < <(echo "${remove_role_line}")

    rm "/lib/svc/manifest/prometheus/${run_binary}.xml" 2>/dev/null
    rmdir /lib/svc/manifest/prometheus 2>/dev/null

    #removing old service logs
    rm "/var/svc/log/prometheus-solaris_exporter:default.log" >/dev/null 2>&1

    #removing hidden MASK on inpreperly removed service
    svccfg -s prometheus/solaris_exporter delcust >/dev/null 2>&1

    #disabling service
    svcadm disable prometheus/solaris_exporter >/dev/null 2>&1

    #remove service from SMF config on new systems (due to removed xml)
    svcadm restart svc:/system/manifest-import >/dev/null 2>&1

    #waiting repository server service initialization
    sleep 3

    #remove service from SMF config on old systems (new systems will only create hidden MASK)
    svccfg delete prometheus/solaris_exporter >/dev/null 2>&1

    #removing hidden MASK if previous svccfg delete was unsuccess
    svccfg -s prometheus/solaris_exporter delcust >/dev/null 2>&1

    # remove service log
    rm /var/svc/log/prometheus-solaris_exporter:default.log 2>/dev/null

    #check if prometheus/solaris_exporter still exists
    echo -n "SMF prometheus/solaris_exporter"
    if svcs prometheus/solaris_exporter >/dev/null 2>&1; then
        echo -n " NOT removed"
        exit 6
    fi
    echo " removed"
}

echo "$0 Script for adding ${run_binary} to Solaris SMF as prometheus/solaris_exporter"
[[ $UID -ne 0 ]] && echo "You need to be ROOT (UID=0)" && exit 4

PATH="/usr/bin:/usr/sbin"
work_dir="$(dirname $0)"; cd "${work_dir}"; work_dir="$(pwd)"

if [[ "$1" == "install" ]] ; then
    RemoveService
    InstallService
elif [[ "$1" == "remove" ]] ; then
    RemoveService
else
    echo "Usage: $0 {install|remove}"
    exit 5
fi