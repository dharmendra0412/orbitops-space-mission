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
  await page.getByLabel('Source URL').fill('https://pds.nasa.gov/')
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
  await page.getByRole('button', { name: /NASA data sources/ }).click()
  await expect(page.getByText('Kaguya SELENE LALT south-polar grid')).toBeVisible()
  await page.getByRole('button', { name: /Fetch original Kaguya LALT label/ }).click()
  await expect(page.getByText('SLN-L-LALT-5-TOPO-GT-SP-IMG-V2.0')).toBeVisible()
  await expect(page.getByText('64,880,640 bytes')).toBeVisible()
  await expect(page.getByText(/not raw laser-shot data or independent geodetic ground truth/i)).toBeVisible()
  await expect(page.getByText(/did not return HTTP 206/)).toBeVisible()
})
