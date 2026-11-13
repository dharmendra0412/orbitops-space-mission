export type MissionResource = {
  id: string
  title: string
  owner: string
  kind: 'DATA ARCHIVE' | 'DATASET GUIDE' | 'SCIENCE REFERENCE' | 'ENGINEERING TOOL' | 'EDUCATIONAL RESOURCE'
  description: string
  url: string
}

export const missionResources: MissionResource[] = [
  {
    id: 'lro-pds',
    title: 'Lunar Reconnaissance Orbiter — PDS archive index',
    owner: 'NASA PDS Geosciences Node',
    kind: 'DATA ARCHIVE',
    description: 'Entry point for LRO instrument archives, including LOLA, Diviner, LROC, and SPICE-related geometry products. The archive page reports release schedules and data availability.',
    url: 'https://pds-geosciences.wustl.edu/missions/lro/',
  },
  {
    id: 'lola',
    title: 'Lunar Orbiter Laser Altimeter (LOLA)',
    owner: 'NASA PDS Geosciences Node',
    kind: 'DATASET GUIDE',
    description: 'Topography and elevation data documentation. The archive explains product access and points users to the Lunar Orbital Data Explorer for the most recent holdings.',
    url: 'https://pds-geosciences.wustl.edu/missions/lro/lola.htm',
  },
  {
    id: 'lro-products',
    title: 'LRO data products',
    owner: 'NASA',
    kind: 'DATASET GUIDE',
    description: 'NASA mission page linking to the Planetary Data System, LROC products, QuickMap, publications, and other LRO resources.',
    url: 'https://science.nasa.gov/mission/lro/data-products/',
  },
  {
    id: 'polar-shadows',
    title: 'Shadows near the Moon’s south pole',
    owner: 'NASA Science',
    kind: 'SCIENCE REFERENCE',
    description: 'NASA science reference for the permanently or persistently shadowed polar terrain context. This is a reference page, not a live illumination feed.',
    url: 'https://science.nasa.gov/resource/shadows-near-the-moons-south-pole/',
  },
  {
    id: 'mission-viz',
    title: 'NASA Mission Visualization',
    owner: 'NASA GitHub',
    kind: 'EDUCATIONAL RESOURCE',
    description: 'NASA-hosted visualization project for learning and reference. ORBITOPS links to the original project and does not claim to embed or reproduce its calculations.',
    url: 'https://nasa.github.io/mission-viz/',
  },
  {
    id: 'gmat',
    title: 'General Mission Analysis Tool (GMAT)',
    owner: 'NASA Software Catalog',
    kind: 'ENGINEERING TOOL',
    description: 'NASA software catalogue entry for GMAT. This is an external engineering tool reference; ORBITOPS does not run GMAT calculations in the browser.',
    url: 'https://software.nasa.gov/software/GSC-19468-1',
  },
  {
    id: 'jpl-cml',
    title: 'Concept Maturity Levels (CML)',
    owner: 'NASA/JPL Dataverse',
    kind: 'SCIENCE REFERENCE',
    description: 'JPL reference dataset supplied for understanding concept maturity levels. Review its dataset citation and terms on the source page.',
    url: 'https://dataverse.jpl.nasa.gov/dataset.xhtml?persistentId=hdl:2014/44299',
  },
  {
    id: 'webb-game',
    title: 'Build it yourself: Webb telescope learning game',
    owner: 'NASA Science',
    kind: 'EDUCATIONAL RESOURCE',
    description: 'NASA educational activity about telescope components and design trade-offs; included as learning material, not as a source of mission telemetry.',
    url: 'https://science.nasa.gov/mission/webb/game-build-it-yourself/',
  },
  {
    id: 'csa-games',
    title: 'Digital games and activities',
    owner: 'Canadian Space Agency',
    kind: 'EDUCATIONAL RESOURCE',
    description: 'External non-U.S. Government educational resource. Its own data-use and reuse conditions apply; NASA does not endorse this organization.',
    url: 'https://www.asc-csa.gc.ca/eng/youth-educators/digital-games-and-activities.asp',
  },
]
