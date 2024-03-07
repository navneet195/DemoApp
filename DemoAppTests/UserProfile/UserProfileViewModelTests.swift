//
//  UserProfileViewModelTests.swift
//  DemoAppTests
//
//  Created by Navnit Baldha on 07/03/24.
//

import Foundation
import XCTest
@testable import DemoApp

class UserProfileViewModelTests: XCTestCase {

    private var viewModel: UserProfileViewModel!
    private var mockComapny: MockCompanyModel!
    private var mockUserModel: MockUserModel!
    private var mockUserNetworkService: MockUserNetworkService!
    override func setUp() {
        mockUserNetworkService = MockUserNetworkService.shared
        viewModel = UserProfileViewModel(userNetworkService: mockUserNetworkService)
    }

    func test_should_get_server_error_messages_when_get_userprofile_api_call() {
        let expectation = expectation(description: #function)
        let errorMessage = "Sorry, the connection to our server failed."
        mockUserNetworkService.userModelList = nil
        viewModel.trigger(by: .getUserData)
        DispatchQueue.main.asyncAfter(deadline: .now() + 2.0) {
            expectation.fulfill()
        }
        wait(for: [expectation], timeout: 4.0)

        XCTAssertEqual(viewModel.userProfileList.count, 0)
        XCTAssertEqual(errorMessage, viewModel.serverErrorMessage)
    }

    func test_should_get_user_data_when_api_call() {
        let expectation = expectation(description: #function)
        let model = UserModel.previewUserModel()
        let result = [model]
        mockUserNetworkService.userModelList = [model]
        viewModel.trigger(by: .getUserData)
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.0) {
            expectation.fulfill()
        }
        wait(for: [expectation], timeout: 2.0)

        XCTAssertEqual(result, viewModel.userProfileList)
        XCTAssertEqual(viewModel.userProfileList.count, 1)

    }

}
