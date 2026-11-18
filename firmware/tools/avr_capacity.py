#!/usr/bin/env python3
"""Measure full linked core + SD on AVR. Capacity ELF only, never a production HEX."""
from pathlib import Path
import subprocess,json,argparse,hashlib,re
parser=argparse.ArgumentParser()
parser.add_argument('--strategy',choices=['baseline','merge-relax','inline-relax'],default='merge-relax')
parser.add_argument('--source-dir',type=Path,help='Isolated copy of ConMT/src for diagnostic studies only')
parser.add_argument('--output-dir',type=Path,help='Separate build directory; required with --source-dir')
args=parser.parse_args()
if args.source_dir and not args.output_dir: parser.error('--source-dir requires a separate --output-dir')
root=Path(__file__).resolve().parents[1]
source_dir=(args.source_dir or root/'ConMT/src').resolve()
workspace=root.parents[1]
cache=workspace/'diagnosis_beton/build_firmware_original'
packages=cache/'arduino-data/packages'
binpath=packages/'arduino/tools/avr-gcc/7.3.0-atmel3.6.1-arduino7/bin'
core=packages/'arduino/hardware/avr/1.8.8/cores/arduino'
variant=packages/'arduino/hardware/avr/1.8.8/variants/standard'
spi=packages/'arduino/hardware/avr/1.8.8/libraries/SPI/src'
sd=cache/'user/libraries/SD/src'
output=(args.output_dir or root/('build-avr-capacity' if args.strategy=='merge-relax' else 'build-avr-capacity-'+args.strategy)).resolve();output.mkdir(parents=True,exist_ok=True)
flags=['-mmcu=atmega328p','-Os','-flto','-mcall-prologues','-fno-inline-small-functions','-fno-inline-functions-called-once','-ffunction-sections','-fdata-sections','-fno-exceptions','-fno-threadsafe-statics','-fno-rtti','-fstack-usage','-std=gnu++11','-DARDUINO=10819','-DARDUINO_ARCH_AVR','-DF_CPU=16000000UL','-I'+str(core),'-I'+str(variant),'-I'+str(spi),'-I'+str(sd),'-I'+str(source_dir)]
if args.strategy!='baseline': flags+=['-mrelax','-fmerge-all-constants']
if args.strategy=='inline-relax': flags.remove('-fno-inline-small-functions')
sources=list(source_dir.rglob('*.cpp'))+[root/'tools/capacity_probe/probe.cpp',spi/'SPI.cpp']+list((sd/'utility').glob('*.cpp'))
objects=[]
for index,source in enumerate(sources):
    obj=output/(str(index)+'.o');objects.append(str(obj))
    subprocess.run([str(binpath/'avr-g++'),*flags,'-c',str(source),'-o',str(obj)],check=True)
# Arduino core archive is a toolchain artifact only, not application code.
archive=cache/'build/core/core.a'
command=[str(binpath/'avr-g++'),'-mmcu=atmega328p','-Os','-flto','-Wl,--gc-sections','-Wl,-Map='+str(output/'capacity.map'),*objects,str(archive),'-lm','-o',str(output/'CAPACITY_ONLY.elf')]
limits='-Wl,--defsym=__TEXT_REGION_LENGTH__=32768,--defsym=__DATA_REGION_LENGTH__=2048'
command.insert(5,limits)
if args.strategy!='baseline': command.insert(5,'-Wl,--relax')
result=subprocess.run(command,text=True,capture_output=True)
if result.returncode:
    (output/'link-errors.txt').write_text(result.stderr)
    # Link with enlarged region solely to quantify overflow; target remains AVR328P.
    command[command.index(limits)]='-Wl,--defsym=__TEXT_REGION_LENGTH__=131072,--defsym=__DATA_REGION_LENGTH__=8192'
    subprocess.run(command,check=True,capture_output=True)
size=subprocess.check_output([str(binpath/'avr-size'),'-A',str(output/'CAPACITY_ONLY.elf')],text=True)
(output/'sections.txt').write_text(size)
sections={line.split()[0]:int(line.split()[1]) for line in size.splitlines() if line.startswith('.')}
flash=sections.get('.text',0)+sections.get('.data',0)
ram=sections.get('.data',0)+sections.get('.bss',0)+sections.get('.noinit',0)
report={'purpose':'capacity probe, never upload','compiler':subprocess.check_output([str(binpath/'avr-g++'),'--version'],text=True).splitlines()[0],'flashBytes':flash,'staticRamBytes':ram,'physicalFlashRemaining':32768-flash,'staticRamRemaining':2048-ram,'fitsStaticLimits':flash<=32768 and ram<=2048,'includes':'shared core/controller/HMI/real SD with disk index/HardwareSerial/confirmed battery adapter; probe clock/sensor/brightness/sound ports','excludes':'verified sensor/RTC drivers, actual stack watermark','clockAssumption':'16MHz for capacity only; not board configuration'}
report['strategy']=args.strategy
report['compilerFlags']=[flag for flag in flags if not flag.startswith('-I')]
report['nativeLinkPassed']=result.returncode==0
report['physicalRegionLimits']={'flash':32768,'sram':2048}
report['probeSourceSha256']=hashlib.sha256((root/'tools/capacity_probe/probe.cpp').read_bytes()).hexdigest()
symbols=subprocess.check_output([str(binpath/'avr-nm'),'-S',str(output/'CAPACITY_ONLY.elf')],text=True)
inputs={}
for line in symbols.splitlines():
    match=re.match(r'[0-9a-f]+ ([0-9a-f]+) [bBdD] (probeInput|probeState)$',line)
    if match:inputs[match[2]]=int(match[1],16)
report['measurementInputsStaticBytes']=sum(inputs.values())
report['measurementInputs']=inputs
report_path=root/('releases/avr-capacity.json' if args.strategy=='merge-relax' else 'releases/avr-capacity-'+args.strategy+'.json')
if args.output_dir:
    report_path=output/'capacity.json'
if args.source_dir:
    report['purpose']='isolated feature-size study, incomplete functionality, never upload'
    report['sourceDirectory']=str(source_dir)
report_path.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
