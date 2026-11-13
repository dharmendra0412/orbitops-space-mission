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
