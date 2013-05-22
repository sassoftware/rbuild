#
# Copyright (c) SAS Institute Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#


import cStringIO as StringIO

from conary.deps import deps

from rpath_proddef import api1 as proddef

try:
    from rpath_proddef import platform_information
except ImportError:
    platform_information = None

def getProductDefinition(cfg, version='1.0', upstream=None, buildFlavors=None):
    p = proddef.ProductDefinition()
    p.setBaseFlavor(str(cfg.buildFlavor))
    p.setProductName('foo')
    p.setProductDescription('foo')
    p.setProductShortname('foo')
    p.setProductVersion(version)
    p.setProductVersionDescription('version description')
    p.setConaryRepositoryHostname('localhost')
    p.setConaryNamespace('foo')
    p.setImageGroup('group-os')
    p.addStage(name='devel', labelSuffix='-devel')
    p.addStage(name='qa', labelSuffix='-qa')
    p.addStage(name='stable', labelSuffix='')
    if upstream:
        if not isinstance(upstream, list):
            upstream = [upstream]
        for item in upstream:
            upstreamName, upstreamLabel = item.split('=', 1)
            p.addSearchPath(upstreamName, upstreamLabel)
    if not buildFlavors:
        buildFlavors = ['']
    arch = deps.getMajorArch(cfg.buildFlavor)
    for idx, buildFlavor in enumerate(buildFlavors):
        buildFlavor = buildFlavor.strip()
        if buildFlavor:
            buildFlavor += ' '
        buildFlavor += 'is: ' + arch
        p.addBuildDefinition(name='build%s' % idx,
                             image=p.imageType('applianceIsoImage'),
                             stages=['devel', 'qa', 'stable'],
                             imageGroup='group-dist',
                             flavor=buildFlavor)

    xmlsubs = p.xmlFactory()
    platformClassifier = xmlsubs.platformClassifierTypeSub(tags='linux')

    if platform_information is None:
        platformInformation = xmlsubs.platformInformationTypeSub(
            originLabel=str(cfg.buildLabel),
        )
        platformInformation.set_platformClassifier(platformClassifier)
        platformInformation.set_bootstrapTrove([])
        platformInformation.set_rpmRequirement([])
    else:
        platformInformation = platform_information.PlatformInformation(
            str(cfg.buildLabel),
            platformClassifier=platformClassifier,
            bootstrapTroves=[],
            rpmRequirements=[],
        )
        def export(*args, **kwargs):
            pass
        platformInformation.export = export

    p.setPlatformInformation(platformInformation)

    return p

def getProductDefinitionString(*args, **kw):
    p = getProductDefinition(*args, **kw)
    stringFile = StringIO.StringIO()
    p.serialize(stringFile)
    stringFile.seek(0)
    return stringFile.read()
