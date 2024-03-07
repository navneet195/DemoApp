//
//  MockCompanyModel.swift
//  DemoAppTests
//
//  Created by Navnit Baldha on 07/03/24.
//

import Foundation
@testable import DemoApp

final class MockCompanyModel {
    func buildCompanyModel() -> CompanyModel {
        return CompanyModel.previewCompanyModel()
    }
}
