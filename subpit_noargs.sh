#!/usr/bin/env bash


# read your RAPid
. ${HOME}/.CLUMEQ_accnt

cat << EOS | qsub -
#PBS -l procs=1
#PBS -o \${PBS_JOBNAME}\${PBS_JOBID}.out
#PBS -e \${PBS_JOBNAME}\${PBS_JOBID}.err
#PBS -N ${1}
#PBS -l walltime=01:00:00:00
#PBS -A ${RAPid}
#PBS -M guziy.sasha@gmail.com

cd \${PBS_O_WORKDIR}

. ${HOME}/activate_py3.6_anaconda.sh

time python -u ${1} >& ${1}.log
EOS
