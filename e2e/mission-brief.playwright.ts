import { expect, test } from '@playwright/test'

async function openMissionBrief(page: import('@playwright/test').Page) {
  await page.goto('/')
  await page.getByRole('button', { name: /Mission brief/ }).click()
  await expect(page.getByRole('heading', { name: 'Build a traceable mission brief' })).toBeVisible()
}

test('mission brief autosaves user input and requirement traceability locally', async ({ page }) => {
  await openMissionBrief(page)

  await page.getByLabel(/Mission name/).fill('Lunar South Pole Survey')
  await page.getByLabel(/Mission objective/).fill('Record source-backed surface science objectives.')
  await page.getByLabel(/Target body \/ region/).fill('Moon — south-polar region; exact site TBD')
  await expect(page.getByText('3 / 9 sections filled')).toBeVisible()
  await expect(page.getByRole('status')).toContainText('Automatically saved in this browser only.')

  await page.getByRole('button', { name: /Add requirement/ }).click()
  await page.getByLabel('Requirement statement').fill('Preserve traceability for every scientific measurement.')
  await page.getByLabel('Target / threshold and units').fill('TBD — source not selected')
  await page.locator('.mission-requirement-row').getByLabel('Source URL').fill('https://pds.nasa.gov/')
  await expect(page.getByText('URL entered · not fetched or validated')).toBeVisible()

  await expect.poll(() => page.evaluate(() => localStorage.getItem('orbitops.mission-brief.v1'))).toContain('Lunar South Pole Survey')
  await page.reload()
  await page.getByRole('button', { name: /Mission brief/ }).click()
  await expect(page.getByLabel(/Mission name/)).toHaveValue('Lunar South Pole Survey')
  await expect(page.getByLabel('Requirement statement')).toHaveValue('Preserve traceability for every scientific measurement.')
})

test('mission brief imports only supported JSON exports and supports export', async ({ page }) => {
  await openMissionBrief(page)
  await page.getByLabel(/Mission name/).fill('Exportable Survey')

  const downloadPromise = page.waitForEvent('download')
  await page.getByRole('button', { name: /Export JSON/ }).click()
  const download = await downloadPromise
  expect(download.suggestedFilename()).toBe('exportable-survey.json')

  const fileInput = page.locator('input[type="file"][accept="application/json,.json"]')
  await fileInput.setInputFiles({
    name: 'imported-brief.json',
    mimeType: 'application/json',
    buffer: Buffer.from(JSON.stringify({
      schema_version: 1,
      brief: {
        missionName: 'Imported Survey',
        objective: 'Imported objective',
        requirements: [{
          id: 'REQ-004',
          statement: 'Imported requirement',
          targetValue: 'TBD',
          sourceUrl: '',
          evidenceNote: 'User supplied',
        }],
      },
    })),
  })
  await expect(page.getByLabel(/Mission name/)).toHaveValue('Imported Survey')
  await expect(page.getByLabel('Requirement statement')).toHaveValue('Imported requirement')

  await fileInput.setInputFiles({
    name: 'unsupported-brief.json',
    mimeType: 'application/json',
    buffer: Buffer.from(JSON.stringify({ schema_version: 99, brief: {} })),
  })
  await expect(page.getByRole('status')).toContainText('Unsupported mission brief export format.')
})


test('Kaguya LALT UI labels the interpolated source and does not claim live pixel access', async ({ page }) => {
  await page.route('**/api/v1/pds3/kaguya/lalt/gt-sp/label', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        source: 'JAXA / DARTS SELENE Data Archive',
        source_url: 'https://data.darts.isas.jaxa.jp/pub/pds3/sln-l-lalt-5-topo-gt-sp-img-v2.0/data/LALT_GT_SP_IMG.lbl',
        retrieved_at: '2026-11-13T12:00:00Z',
        product_file: 'LALT_GT_SP_IMG.IMG',
        metadata: {
          dataset_id: 'SLN-L-LALT-5-TOPO-GT-SP-IMG-V2.0',
          product_id: 'LALT_GT_SP_IMG',
          lines: 1408,
          line_samples: 11520,
          sample_type: 'PC_REAL (little-endian IEEE 754 float32)',
          sample_bits: 32,
          image_bytes: 64880640,
          dummy_value_km: 99.999,
          height_unit: 'km',
          reference_sphere_radius_km: 1737.4,
          coordinate_system: 'MEAN EARTH/POLAR AXIS OF DE421',
          coordinate_system_type: 'BODY-FIXED ROTATING',
          map_projection_type: 'N/A',
          maximum_latitude_degrees: -79.00390625,
          minimum_latitude_degrees: -89.99609375,
          westernmost_longitude_degrees: 0.015625,
          easternmost_longitude_degrees: 359.984375,
          latitude_pixels_per_degree: 128,
          longitude_pixels_per_degree: 32,
        },
        validation_scope: 'Interpolated grid derived from LALT_LGT_TS; not raw laser-shot data or independent geodetic ground truth.',
      }),
    })
  })

  await page.goto('/')
  await page.locator('.side-nav').getByRole('button', { name: 'NASA data sources' }).click()
  await expect(page.getByText('Kaguya SELENE LALT south-polar grid')).toBeVisible()
  await page.getByRole('button', { name: /Fetch original Kaguya LALT label/ }).click()
  await expect(page.getByText('SLN-L-LALT-5-TOPO-GT-SP-IMG-V2.0', { exact: true })).toBeVisible()
  await expect(page.getByText('64,880,640 bytes')).toBeVisible()
  await expect(page.getByText(/not raw laser-shot data or independent geodetic ground truth/i)).toBeVisible()
  await expect(page.getByText(/did not return HTTP 206/)).toBeVisible()
})


test('LOLA browser workflow uses source label, bounded pixel, and row-profile API responses', async ({ page }) => {
  await page.route('**/api/v1/pds3/lola/gdr/ldem-85s-40m/label', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        source: 'NASA PDS Geosciences Node',
        source_url: 'https://pds-geosciences.wustl.edu/source.lbl',
        retrieved_at: '2026-11-13T12:00:00Z',
        label_format: 'PDS3',
        product_file: 'LDEM_85S_40M.IMG',
        metadata: {
          PDS_VERSION_ID: 'PDS3',
          FILE_NAME: 'LDEM_85S_40M.IMG',
          DATA_SET_ID: 'LRO-L-LOLA-4-GDR-V1.0',
          PRODUCT_VERSION_ID: 'V2.0',
          TARGET_NAME: 'MOON',
          MAP_PROJECTION_TYPE: 'POLAR STEREOGRAPHIC',
          KEYWORD_LATITUDE_TYPE: 'PLANETOCENTRIC',
          POSITIVE_LONGITUDE_DIRECTION: 'EAST',
          COORDINATE_SYSTEM_NAME: 'MEAN EARTH/POLAR AXIS OF DE421',
          CENTER_LATITUDE: '-90 <deg>',
          CENTER_LONGITUDE: '0 <deg>',
          MAP_PROJECTION_ROTATION: '0.0',
          A_AXIS_RADIUS: '1737.4 <km>',
          B_AXIS_RADIUS: '1737.4 <km>',
          C_AXIS_RADIUS: '1737.4 <km>',
          MAP_SCALE: '40 <m/pix>',
          LINE_PROJECTION_OFFSET: '3791.5 <pix>',
          SAMPLE_PROJECTION_OFFSET: '3791.5 <pix>',
          LINES: '7584',
          LINE_SAMPLES: '7584',
        },
        note: 'Source PDS3 label metadata only.',
      }),
    })
  })

  await page.route('**/api/v1/pds3/lola/gdr/ldem-85s-40m/pixel*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        source: 'NASA PDS Geosciences Node',
        source_url: 'https://pds-geosciences.wustl.edu/LDEM_85S_40M.IMG',
        label_source_url: 'https://pds-geosciences.wustl.edu/LDEM_85S_40M.LBL',
        retrieved_at: '2026-11-13T12:00:01Z',
        product_file: 'LDEM_85S_40M.IMG',
        line_index: 3791,
        sample_index: 3791,
        byte_range_inclusive: { start: 57509470, end: 57509471 },
        raw_dn: -1295,
        height_m: -647.5,
        planetary_radius_m: 1736752.5,
        planetocentric_latitude_degrees: -90,
        east_longitude_degrees: 0,
        units: { raw_dn: 'signed 16-bit integer', height: 'm', planetary_radius: 'm' },
        coordinate_reference: 'MEAN EARTH/POLAR AXIS OF DE421',
        validation_scope: 'One exact two-byte source sample.',
      }),
    })
  })

  await page.route('**/api/v1/pds3/lola/gdr/ldem-85s-40m/profile*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        source: 'NASA PDS Geosciences Node',
        source_url: 'https://pds-geosciences.wustl.edu/LDEM_85S_40M.IMG',
        label_source_url: 'https://pds-geosciences.wustl.edu/LDEM_85S_40M.LBL',
        retrieved_at: '2026-11-13T12:00:02Z',
        product_file: 'LDEM_85S_40M.IMG',
        line_index: 3791,
        start_sample_index: 3791,
        sample_count: 3,
        sample_spacing_m: 40,
        profile_span_m: 80,
        byte_range_inclusive: { start: 57509470, end: 57509475 },
        coordinate_reference: 'MEAN EARTH/POLAR AXIS OF DE421',
        points: [
          { sample_index: 3791, raw_dn: -1295, height_m: -647.5, planetary_radius_m: 1736752.5, planetocentric_latitude_degrees: -90, east_longitude_degrees: 0 },
          { sample_index: 3792, raw_dn: -1294, height_m: -647, planetary_radius_m: 1736753, planetocentric_latitude_degrees: -89.999, east_longitude_degrees: 45 },
          { sample_index: 3793, raw_dn: -1293, height_m: -646.5, planetary_radius_m: 1736753.5, planetocentric_latitude_degrees: -89.999, east_longitude_degrees: 90 },
        ],
        validation_scope: 'Three bounded original samples.',
      }),
    })
  })

  await page.goto('/')
  await page.locator('.side-nav').getByRole('button', { name: 'NASA data sources' }).click()
  await page.getByRole('button', { name: /Fetch original LOLA label metadata/ }).click()
  await expect(page.getByText('LDEM_85S_40M.IMG')).toBeVisible()
  await page.getByRole('button', { name: /Fetch actual NASA LOLA pixel/ }).click()
  await expect(page.getByText('-1295', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: /Fetch real elevation profile/ }).click()
  await expect(page.getByText('LOLA source elevation profile')).toBeVisible()
  await expect(page.getByText('3 original samples · line 3791 · 40 m/pixel')).toBeVisible()
})


test('NASA PDS browser search resolves original file inventory without synthesizing records', async ({ page }) => {
  await page.route('**/api/v1/pds/search*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        source: 'NASA Planetary Data System Search API',
        source_url: 'https://pds.nasa.gov/api/search?keyword=LOLA',
        api_documentation: 'https://nasa-pds.github.io/pds-api/',
        retrieved_at: '2026-11-13T12:00:00Z',
        query: { keywords: 'LOLA', limit: 10 },
        response: {
          summary: { hits: 1 },
          data: [{
            lidvid: 'urn:nasa:pds:lro_lola_rdr:data_gridded::1.0',
            title: 'LOLA Gridded Data',
          }],
        },
      }),
    })
  })

  let hierarchyPage = 0
  await page.route('**/api/v1/pds/products/**/members*', async (route) => {
    hierarchyPage += 1
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        source: 'NASA Planetary Data System Search API',
        source_url: 'https://pds.nasa.gov/api/search/collections/example/members',
        api_documentation: 'https://nasa-pds.github.io/pds-api/',
        retrieved_at: '2026-11-13T12:00:02Z',
        identifier: 'urn:nasa:pds:lro_lola_rdr:data_gridded::1.0',
        depth: 1,
        page: { limit: 100, sort: 'ops:Harvest_Info.ops:harvest_date_time', search_after: hierarchyPage > 1 ? 'cursor-1' : null },
        next_search_after: hierarchyPage === 1 ? 'cursor-1' : null,
        response: {
          data: hierarchyPage === 1
            ? [
                { id: 'urn:nasa:pds:lro_lola_rdr:data_gridded:ldem_85s_40m::1.0', title: 'LOLA 85S 40M image', type: 'Product_Observational' },
                { id: 'urn:nasa:pds:lro_lola_rdr:data_gridded:ldem_80s_40m::1.0', title: 'LOLA 80S 40M image', type: 'Product_Observational' },
              ]
            : [
                { id: 'urn:nasa:pds:lro_lola_rdr:data_gridded:ldem_80s_40m::1.0', title: 'LOLA 80S 40M image', type: 'Product_Observational' },
                { id: 'urn:nasa:pds:lro_lola_rdr:data_gridded:ldem_75s_40m::1.0', title: 'LOLA 75S 40M image', type: 'Product_Observational' },
              ],
        },
      }),
    })
  })

  await page.route('**/api/v1/pds/products/**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        source: 'NASA Planetary Data System Search API',
        source_url: 'https://pds.nasa.gov/api/products/urn:nasa:pds:lro_lola_rdr:data_gridded::1.0',
        api_documentation: 'https://nasa-pds.github.io/pds-api/',
        retrieved_at: '2026-11-13T12:00:01Z',
        identifier: 'urn:nasa:pds:lro_lola_rdr:data_gridded::1.0',
        response: {
          meta: {
            'ops:Label_File_Info': {
              'ops:file_name': 'LDEM_85S_40M.LBL',
              'ops:file_ref': 'urn:nasa:pds:lro_lola_rdr:data_gridded::1.0/LDEM_85S_40M.LBL',
              'ops:file_size': 4096,
              'ops:mime_type': 'text/plain',
            },
            'ops:Data_Files': [{
              'ops:file_name': 'LDEM_85S_40M.IMG',
              'ops:file_ref': 'urn:nasa:pds:lro_lola_rdr:data_gridded::1.0/LDEM_85S_40M.IMG',
              'ops:file_size': 115034112,
              'ops:mime_type': 'application/octet-stream',
            }],
          },
        },
      }),
    })
  })

  await page.goto('/')
  await page.locator('.side-nav').getByRole('button', { name: 'NASA data sources' }).click()
  await page.getByLabel('Product keywords').fill('LOLA')
  await page.getByRole('button', { name: 'Search PDS' }).click()
  await expect(page.getByText('LOLA Gridded Data')).toBeVisible()
  await expect(page.locator('.pds-product-card').getByText('urn:nasa:pds:lro_lola_rdr:data_gridded::1.0')).toBeVisible()
  await page.getByRole('button', { name: 'Resolve source metadata' }).click()
  await expect(page.locator('.pds-file-row').getByText('LDEM_85S_40M.LBL')).toBeVisible()
  await expect(page.locator('.pds-file-row').getByText('115034112 bytes')).toBeVisible()
  await page.getByRole('button', { name: /Browse direct children/ }).click()
  await expect(page.getByText('LOLA 85S 40M image')).toBeVisible()
  await expect(page.getByText('LOLA 80S 40M image')).toBeVisible()
  await expect(page.getByText('1 unique child records loaded across archive pages')).toHaveCount(0)
  await page.getByRole('button', { name: /Load next 100 source records/ }).click()
  await expect(page.getByText('3 unique child records loaded across archive pages')).toBeVisible()
  await expect(page.getByText('LOLA 75S 40M image')).toBeVisible()
  await expect(page.getByText('LOLA 80S 40M image')).toHaveCount(1)
})


test('NASA PDS upstream failures remain visible and do not create fallback records', async ({ page }) => {
  await page.route('**/api/v1/pds/search*', async (route) => {
    await route.fulfill({
      status: 503,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'NASA PDS Search API is temporarily unavailable. Retry later or consult the mission archive index.' }),
    })
  })

  await page.goto('/')
  await page.locator('.side-nav').getByRole('button', { name: 'NASA data sources' }).click()
  await page.getByLabel('Product keywords').fill('LOLA')
  await page.getByRole('button', { name: 'Search PDS' }).click()
  await expect(page.getByRole('alert')).toContainText('NASA PDS Search API is temporarily unavailable.')
  await expect(page.getByText('Returned 0 product records')).toHaveCount(0)
  await expect(page.locator('.pds-product-card')).toHaveCount(0)
})
