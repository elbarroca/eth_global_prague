export function add0x(data: string): string {
    if (data.includes('0x')) {
        return data
    }

    return '0x' + data
}